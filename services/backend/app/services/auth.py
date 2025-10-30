from __future__ import annotations

import hashlib
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppSettings
from app.integrations.google import GoogleOAuthClient, GoogleProfile
from app.integrations.sms import SMSProvider
from app.models import LoginChallenge, RefreshToken, User
from app.schemas.auth import (
    AuthProvider,
    LoginChallengeResponse,
    SMSLoginRequest,
    TokenExchangeRequest,
    TokenRefreshRequest,
    TokenResponse,
)


class AuthService:
    """Authentication workflows covering SMS OTP and Google OAuth flows."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppSettings,
        sms_provider: SMSProvider,
        google_client: GoogleOAuthClient,
    ):
        self._session = session
        self._settings = settings
        self._sms_provider = sms_provider
        self._google_client = google_client

    async def initiate_sms_login(self, payload: SMSLoginRequest) -> LoginChallengeResponse:
        phone_number = self._normalize_phone(payload.phone_number, payload.country_code)
        if not phone_number:
            raise ValueError("Phone number is invalid.")

        user = await self._find_user_by_phone(phone_number)
        otp_code = self._generate_otp()
        now = self._now()
        expires_at = now + timedelta(seconds=self._settings.otp_expiry_seconds)

        challenge = LoginChallenge(
            id=uuid4(),
            user_id=user.id if user else None,
            provider=AuthProvider.SMS.value,
            phone_number=phone_number,
            code_hash=self._hash_secret(otp_code),
            expires_at=expires_at,
            attempts=0,
            max_attempts=max(1, self._settings.otp_attempt_limit),
            payload={
                "country_code": payload.country_code,
                "locale": payload.locale or "zh-CN",
            },
        )
        self._session.add(challenge)
        await self._session.flush()

        await self._sms_provider.send_otp(
            phone_number=phone_number,
            code=otp_code,
            sender_id=self._settings.sms_sender_id,
            locale=payload.locale,
        )

        return LoginChallengeResponse(
            channel=AuthProvider.SMS,
            challenge_id=str(challenge.id),
            expires_in=self._settings.otp_expiry_seconds,
            detail="OTP dispatched for SMS verification.",
        )

    async def exchange_token(self, payload: TokenExchangeRequest) -> TokenResponse:
        if not payload.code:
            raise ValueError("Verification/OAuth code is required.")
        if payload.provider == AuthProvider.SMS:
            if not payload.challenge_id:
                raise ValueError("challenge_id is required for SMS authentication.")
            user = await self._complete_sms_login(payload.challenge_id, payload.code)
            return await self._issue_tokens(user, session_id=payload.session_id)

        if payload.provider == AuthProvider.GOOGLE:
            profile = await self._google_client.exchange_code(payload.code, payload.redirect_uri)
            user = await self._upsert_google_user(profile)
            return await self._issue_tokens(user, session_id=payload.session_id)

        raise ValueError(f"Unsupported auth provider {payload.provider}.")

    async def refresh_token(self, payload: TokenRefreshRequest) -> TokenResponse:
        if not payload.refresh_token:
            raise ValueError("Refresh token must be supplied.")
        hashed = self._hash_secret(payload.refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == hashed)
        result = await self._session.execute(stmt)
        token = result.scalar_one_or_none()
        if not token:
            raise ValueError("Refresh token is invalid.")

        now = self._now()
        if token.expires_at <= now:
            raise ValueError("Refresh token has expired.")
        if token.revoked_at is not None:
            raise ValueError("Refresh token has been revoked.")

        user = token.user or await self._session.get(User, token.user_id)
        if not user:
            raise ValueError("Associated user could not be resolved.")

        token.revoked_at = now
        await self._session.flush()

        return await self._issue_tokens(
            user,
            session_id=payload.session_id,
            user_agent=payload.user_agent,
            ip_address=payload.ip_address,
        )

    async def _complete_sms_login(self, challenge_id: str, code: str) -> User:
        try:
            challenge_uuid = UUID(challenge_id)
        except ValueError as exc:
            raise ValueError("challenge_id is malformed.") from exc

        challenge = await self._session.get(LoginChallenge, challenge_uuid)
        if not challenge:
            raise ValueError("SMS challenge not found.")
        if challenge.provider != AuthProvider.SMS.value:
            raise ValueError("Challenge provider mismatch.")

        now = self._now()
        if challenge.verified_at is not None:
            raise ValueError("Challenge has already been completed.")
        if challenge.expires_at <= now:
            raise ValueError("Challenge has expired; please request a new OTP.")
        if challenge.attempts >= challenge.max_attempts:
            raise ValueError("Maximum verification attempts exceeded.")

        if challenge.code_hash != self._hash_secret(code):
            challenge.attempts += 1
            await self._session.flush()
            raise ValueError("Verification code is incorrect.")

        challenge.verified_at = now
        phone_number = challenge.phone_number
        if not phone_number:
            raise ValueError("Challenge missing phone number.")

        user = await self._get_or_create_user_by_phone(phone_number)
        challenge.user_id = user.id
        await self._session.flush()
        return user

    async def _upsert_google_user(self, profile: GoogleProfile) -> User:
        stmt = select(User).where(User.external_id == profile.subject).limit(1)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.email = profile.email
            user.display_name = profile.name
            await self._session.flush()
            return user

        user = User(
            external_id=profile.subject,
            email=profile.email,
            display_name=profile.name,
            locale="zh-CN",
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def _issue_tokens(
        self,
        user: User,
        *,
        session_id: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        secret = (
            self._settings.jwt_secret_key.get_secret_value()
            if self._settings.jwt_secret_key
            else "mindwell-local-dev-secret"
        )
        now = self._now()
        expires_at = now + timedelta(seconds=self._settings.access_token_ttl)
        refresh_expiry = now + timedelta(seconds=self._settings.refresh_token_ttl)

        payload: dict[str, Any] = {
            "sub": str(user.id),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._settings.app_name,
        }
        if session_id:
            payload["sid"] = session_id

        access_token = jwt.encode(payload, secret, algorithm=self._settings.jwt_algorithm)
        refresh_token = secrets.token_urlsafe(48)

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=self._hash_secret(refresh_token),
            issued_at=now,
            expires_at=refresh_expiry,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._session.add(refresh_record)
        await self._session.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._settings.access_token_ttl,
        )

    async def _find_user_by_phone(self, phone_number: str) -> User | None:
        stmt = select(User).where(User.phone_number == phone_number).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_create_user_by_phone(self, phone_number: str) -> User:
        user = await self._find_user_by_phone(phone_number)
        if user:
            return user

        user = User(phone_number=phone_number, locale="zh-CN")
        self._session.add(user)
        await self._session.flush()
        return user

    def _hash_secret(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _generate_otp(self) -> str:
        return "".join(random.choices("0123456789", k=6))

    def _normalize_phone(self, phone_number: str, country_code: str | None) -> str:
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        if not digits:
            return ""
        prefix = country_code or "+86"
        prefix_digits = prefix if prefix.startswith("+") else f"+{prefix}"
        if prefix_digits == "+86" and len(digits) > 11:
            digits = digits[-11:]
        return f"{prefix_digits}{digits}" if digits else ""

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)
