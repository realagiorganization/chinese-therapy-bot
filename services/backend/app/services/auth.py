from __future__ import annotations

import hashlib
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppSettings
from app.models import RefreshToken, User
from app.schemas.auth import DemoLoginRequest, TokenRefreshRequest, TokenResponse
from app.services.demo_codes import DemoCodeEntry, DemoCodeRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OAuth2Identity:
    """Normalized identity payload extracted from oauth2-proxy headers."""

    subject: str
    email: str
    name: str | None = None


class AuthService:
    """Authentication workflows backed by oauth2-proxy and demo code allowlists."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppSettings,
        demo_registry: DemoCodeRegistry,
    ):
        self._session = session
        self._settings = settings
        self._demo_registry = demo_registry

    async def create_session_from_oauth(
        self,
        identity: OAuth2Identity,
        *,
        session_id: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Issue MindWell tokens for a user authenticated by oauth2-proxy."""
        email = identity.email.strip().lower()
        if not email:
            raise ValueError("OAuth2 identity is missing email claims.")

        subject = identity.subject.strip() or email
        user = await self._upsert_oauth_user(subject=subject, email=email, name=identity.name)
        limit = self._resolve_token_limit(user)
        await self._enforce_token_limit(user, limit)

        logger.debug("Issuing tokens for oauth2 user %s (limit=%s)", user.id, limit)
        return await self._issue_tokens(
            user,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def login_with_demo_code(
        self,
        payload: DemoLoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Exchange an allowlisted demo code for access tokens."""
        entry = self._demo_registry.lookup(payload.code)
        if not entry:
            raise ValueError("Демо-код не найден или не разрешён.")

        user = await self._get_or_create_demo_user(entry)
        limit = self._resolve_token_limit(user, override=entry.token_limit)
        await self._enforce_token_limit(user, limit)

        logger.debug(
            "Issuing tokens for demo code %s (user=%s, limit=%s)",
            entry.code,
            user.id,
            limit,
        )
        return await self._issue_tokens(
            user,
            session_id=payload.session_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def refresh_token(self, payload: TokenRefreshRequest) -> TokenResponse:
        """Rotate refresh token and mint a new access token pair."""
        if not payload.refresh_token:
            raise ValueError("Необходимо указать refresh_token.")

        hashed = self._hash_secret(payload.refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == hashed)
        result = await self._session.execute(stmt)
        token = result.scalar_one_or_none()
        if not token:
            raise ValueError("Refresh token не найден или уже отозван.")

        now = self._now()
        if token.expires_at <= now:
            raise ValueError("Срок действия refresh token истёк.")
        if token.revoked_at is not None:
            raise ValueError("Refresh token был отозван.")

        user = token.user or await self._session.get(User, token.user_id)
        if not user:
            raise ValueError("Пользователь для refresh token не найден.")

        token.revoked_at = now

        limit = self._resolve_token_limit(user)
        await self._enforce_token_limit(user, limit)

        logger.debug("Refreshing tokens for user %s (limit=%s)", user.id, limit)
        return await self._issue_tokens(
            user,
            session_id=payload.session_id,
            user_agent=payload.user_agent,
            ip_address=payload.ip_address,
        )

    async def _upsert_oauth_user(self, *, subject: str, email: str, name: str | None) -> User:
        stmt = select(User).where(User.external_id == subject).limit(1)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()

        display_name = (name or "").strip() or email.split("@", 1)[0]

        default_limit = max(1, self._settings.auth_default_token_limit)
        default_chat_quota = max(0, self._settings.chat_token_default_quota)

        if user:
            if user.email != email:
                user.email = email
            if display_name and user.display_name != display_name:
                user.display_name = display_name
            if not user.account_type or user.account_type == "legacy":
                user.account_type = "email"
            if not user.token_limit or user.token_limit <= 0:
                user.token_limit = default_limit
            if user.demo_code is not None:
                user.demo_code = None
            self._sync_chat_quota(user, default_chat_quota)
            await self._session.flush()
            return user

        user = User(
            external_id=subject,
            email=email,
            display_name=display_name,
            locale="zh-CN",
            account_type="email",
            token_limit=default_limit,
        )
        self._sync_chat_quota(user, default_chat_quota)
        self._session.add(user)
        await self._session.flush()
        return user

    async def _get_or_create_demo_user(self, entry: DemoCodeEntry) -> User:
        stmt = select(User).where(User.demo_code == entry.code).limit(1)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()

        display_name = entry.label or f"Demo {entry.code}"
        email = self._demo_email(entry.code)
        token_limit = entry.token_limit or self._settings.auth_demo_token_limit
        chat_quota = (
            entry.chat_token_quota
            if entry.chat_token_quota is not None
            else self._settings.chat_token_demo_quota
        )

        if user:
            if user.account_type != "demo":
                user.account_type = "demo"
            if user.display_name != display_name:
                user.display_name = display_name
            if user.email != email:
                user.email = email
            if not user.token_limit or user.token_limit <= 0 or entry.token_limit:
                user.token_limit = max(1, token_limit)
            self._sync_chat_quota(user, chat_quota)
            await self._session.flush()
            return user

        user = User(
            external_id=f"demo:{entry.code}",
            email=email,
            display_name=display_name,
            locale="zh-CN",
            account_type="demo",
            demo_code=entry.code,
            token_limit=max(1, token_limit),
        )
        self._sync_chat_quota(user, chat_quota)
        self._session.add(user)
        await self._session.flush()
        return user

    async def _enforce_token_limit(self, user: User, limit: int) -> None:
        limit = max(0, limit)
        if limit == 0:
            return

        now = self._now()
        stmt = (
            select(func.count(RefreshToken.id))
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        active_tokens = result.scalar_one() or 0
        if active_tokens >= limit:
            raise ValueError("Достигнут лимит активных сессий для этого аккаунта.")

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
            token_type="bearer",  # nosec B106
            expires_in=self._settings.access_token_ttl,
        )

    def _resolve_token_limit(self, user: User, *, override: int | None = None) -> int:
        if override and override > 0:
            return override
        if user.token_limit and user.token_limit > 0:
            return user.token_limit
        if user.account_type == "demo":
            return max(1, self._settings.auth_demo_token_limit)
        return max(1, self._settings.auth_default_token_limit)

    def _hash_secret(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _demo_email(self, code: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")
        slug = slug or "demo"
        return f"{slug}@demo.local"

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def _sync_chat_quota(self, user: User, quota: int) -> None:
        normalized_quota = quota if quota >= 0 else 0
        user.chat_token_quota = normalized_quota
        if user.chat_tokens_remaining is None:
            user.chat_tokens_remaining = normalized_quota
        else:
            if user.chat_tokens_remaining > normalized_quota:
                user.chat_tokens_remaining = normalized_quota
            if user.chat_tokens_remaining < 0:
                user.chat_tokens_remaining = 0


__all__ = ["AuthService", "OAuth2Identity"]
