from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.integrations.google import GoogleOAuthClient
from app.integrations.wechat import WeChatProfile
from app.integrations.sms import SMSProvider
from app.models.entities import LoginChallenge, RefreshToken, User
from app.schemas.auth import (
    AuthProvider,
    SMSLoginRequest,
    TokenExchangeRequest,
)
from app.services.auth import AuthService


class StubSMSProvider(SMSProvider):
    """Capture OTP payloads without external delivery."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    async def send_otp(
        self,
        phone_number: str,
        code: str,
        *,
        sender_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        self.sent_messages.append(
            {
                "phone_number": phone_number,
                "code": code,
                "sender_id": sender_id,
                "locale": locale,
            }
        )


@pytest_asyncio.fixture()
async def auth_session() -> AsyncSession:
    """Provide an isolated in-memory database session for auth tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(LoginChallenge.__table__.create)
        await conn.run_sync(RefreshToken.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        yield session

    await engine.dispose()


def make_auth_service(
    session: AsyncSession, sms_provider: StubSMSProvider, wechat_client: StubWeChatClient | None = None
) -> AuthService:
    settings = AppSettings(
        JWT_SECRET_KEY="unit-test-secret",
        OTP_EXPIRY_SECONDS=120,
        OTP_ATTEMPT_LIMIT=2,
        ACCESS_TOKEN_TTL=120,
        REFRESH_TOKEN_TTL=3600,
    )
    google_client = GoogleOAuthClient(settings)
    wechat_client = wechat_client or StubWeChatClient()
    return AuthService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
        google_client=google_client,
        wechat_client=wechat_client,
    )


@pytest.mark.asyncio
async def test_initiate_sms_login_creates_challenge_and_sends_code(
    auth_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    sms_provider = StubSMSProvider()
    service = make_auth_service(auth_session, sms_provider)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.utcnow())

    monkeypatch.setattr(AuthService, "_generate_otp", lambda self: "123456")

    payload = SMSLoginRequest(phone_number="13800138000", country_code="+86", locale="zh-CN")
    response = await service.initiate_sms_login(payload)

    assert response.channel is AuthProvider.SMS
    assert response.challenge_id
    assert sms_provider.sent_messages
    sent = sms_provider.sent_messages[-1]
    assert sent["phone_number"] == "+8613800138000"
    assert sent["code"] == "123456"

    challenge = await auth_session.get(LoginChallenge, UUID(response.challenge_id))
    assert challenge is not None
    assert challenge.phone_number == "+8613800138000"
    assert challenge.code_hash != "123456"
    assert challenge.expires_at > challenge.created_at


@pytest.mark.asyncio
async def test_exchange_token_verifies_code_and_persists_refresh_token(
    auth_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    sms_provider = StubSMSProvider()
    service = make_auth_service(auth_session, sms_provider)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.utcnow())

    monkeypatch.setattr(AuthService, "_generate_otp", lambda self: "654321")

    challenge = await service.initiate_sms_login(
        SMSLoginRequest(phone_number="13800138000", country_code="+86", locale="zh-CN")
    )

    token_response = await service.exchange_token(
        TokenExchangeRequest(
            provider=AuthProvider.SMS,
            code="654321",
            challenge_id=challenge.challenge_id,
        )
    )

    assert token_response.access_token
    assert token_response.refresh_token

    users_result = await auth_session.execute(select(User))
    users = users_result.scalars().all()
    assert len(users) == 1

    tokens_result = await auth_session.execute(select(RefreshToken))
    token_records = tokens_result.scalars().all()
    assert len(token_records) == 1
    assert token_records[0].token_hash

    saved_challenge = await auth_session.get(LoginChallenge, UUID(challenge.challenge_id))
    assert saved_challenge is not None
    assert saved_challenge.verified_at is not None


@pytest.mark.asyncio
async def test_exchange_token_wechat_creates_user(auth_session: AsyncSession) -> None:
    sms_provider = StubSMSProvider()
    wechat_client = StubWeChatClient()
    service = make_auth_service(auth_session, sms_provider, wechat_client)

    token_response = await service.exchange_token(
        TokenExchangeRequest(
            provider=AuthProvider.WECHAT,
            code="wechat-dev-code",
        )
    )

    assert token_response.access_token
    assert token_response.refresh_token

    stmt = select(User).where(User.external_id == "wechat-union-edoc-ved-tahcew")
    result = await auth_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.display_name.startswith("测试用户")


@pytest.mark.asyncio
async def test_exchange_token_enforces_attempt_limits(
    auth_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    sms_provider = StubSMSProvider()
    service = make_auth_service(auth_session, sms_provider)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.utcnow())

    monkeypatch.setattr(AuthService, "_generate_otp", lambda self: "111222")

    challenge = await service.initiate_sms_login(
        SMSLoginRequest(phone_number="13800138000", country_code="+86", locale="zh-CN")
    )

    request = TokenExchangeRequest(
        provider=AuthProvider.SMS,
        code="000000",
        challenge_id=challenge.challenge_id,
    )

    # First incorrect attempt increments the counter.
    with pytest.raises(ValueError) as first_error:
        await service.exchange_token(request)
    assert "incorrect" in str(first_error.value).lower()

    # Second incorrect attempt still returns incorrect code.
    with pytest.raises(ValueError):
        await service.exchange_token(request)

    # Third attempt exceeds max_attempts and raises the guardrail message.
    with pytest.raises(ValueError) as overflow_error:
        await service.exchange_token(request)
    assert "maximum verification attempts" in str(overflow_error.value).lower()
class StubWeChatClient:
    """Deterministic WeChat OAuth stub returning synthetic profiles."""

    async def exchange_code(
        self, code: str, redirect_uri: str | None = None
    ) -> WeChatProfile:
        if not code:
            raise ValueError("Authorization code is missing.")
        digest = code[::-1]
        open_id = f"wechat-{digest}"
        union_id = f"wechat-union-{digest}"
        nickname = f"测试用户{len(code)}"
        return WeChatProfile(
            open_id=open_id,
            union_id=union_id,
            nickname=nickname,
            locale="zh-CN",
        )
