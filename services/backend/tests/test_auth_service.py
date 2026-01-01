from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.models.entities import RefreshToken, User
from app.schemas.auth import DemoLoginRequest, RegistrationRequest, TokenRefreshRequest
from app.services.auth import AuthService, OAuth2Identity
from app.services.demo_codes import DemoCodeEntry


class StubDemoRegistry:
    """In-memory registry used in unit tests."""

    def __init__(self, entries: Iterable[DemoCodeEntry] = ()):
        self._entries: dict[str, DemoCodeEntry] = {}
        self._fallback: dict[str, DemoCodeEntry | None] = {}
        for entry in entries:
            key = entry.code.strip()
            self._entries[key] = entry
            lowered = key.casefold()
            if lowered in self._fallback:
                self._fallback[lowered] = None
            else:
                self._fallback[lowered] = entry

    def lookup(self, code: str | None) -> DemoCodeEntry | None:
        if not code:
            return None
        normalized = code.strip()
        if not normalized:
            return None
        direct = self._entries.get(normalized)
        if direct:
            return direct
        lowered = normalized.casefold()
        if lowered in self._fallback:
            return self._fallback[lowered]
        return None


@pytest_asyncio.fixture()
async def auth_session() -> AsyncSession:
    """Provide an isolated in-memory database session for auth tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(RefreshToken.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def make_auth_service(
    session: AsyncSession,
    registry: StubDemoRegistry,
    *,
    default_chat_quota: int = 50,
    demo_chat_quota: int = 10,
) -> AuthService:
    settings = AppSettings(
        JWT_SECRET_KEY="unit-test-secret",
        ACCESS_TOKEN_TTL=120,
        REFRESH_TOKEN_TTL=3600,
        CHAT_TOKEN_DEFAULT_QUOTA=default_chat_quota,
        CHAT_TOKEN_DEMO_QUOTA=demo_chat_quota,
    )
    return AuthService(session=session, settings=settings, demo_registry=registry)


@pytest.mark.asyncio
async def test_create_session_from_oauth_creates_user_and_tokens(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.now(timezone.utc))

    identity = OAuth2Identity(subject="azure-ad:123", email="user@example.com", name="Test User")
    tokens = await service.create_session_from_oauth(identity, session_id="sess-1")

    assert tokens.access_token
    assert tokens.refresh_token

    users_result = await auth_session.execute(select(User))
    users = users_result.scalars().all()
    assert len(users) == 1
    assert users[0].email == "user@example.com"
    assert users[0].account_type == "email"
    assert users[0].chat_token_quota == 50
    assert users[0].chat_tokens_remaining == 50

    refresh_result = await auth_session.execute(select(RefreshToken))
    refresh_tokens = refresh_result.scalars().all()
    assert len(refresh_tokens) == 1
    assert refresh_tokens[0].revoked_at is None


@pytest.mark.asyncio
async def test_login_with_demo_code_honours_allowlist(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry(
        [
            DemoCodeEntry(
                code="DEMO-42",
                label="Demo Account",
                chat_token_quota=7,
            )
        ]
    )
    service = make_auth_service(auth_session, registry, demo_chat_quota=5)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.now(timezone.utc))

    payload = DemoLoginRequest(code="demo-42")
    tokens = await service.login_with_demo_code(payload, user_agent="pytest")

    assert tokens.access_token

    users_result = await auth_session.execute(select(User))
    user = users_result.scalar_one()
    assert user.account_type == "demo"
    assert user.demo_code == "DEMO-42"
    assert user.chat_token_quota == 7
    assert user.chat_tokens_remaining == 7


@pytest.mark.asyncio
async def test_demo_code_accounts_are_isolated(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry(
        [
            DemoCodeEntry(
                code="TEAM-ALPHA",
                label="Team Alpha Upper",
                chat_token_quota=7,
            ),
            DemoCodeEntry(
                code="Team Alpha",
                label="Team Alpha Mixed",
                chat_token_quota=7,
            ),
        ]
    )
    service = make_auth_service(auth_session, registry, demo_chat_quota=5)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(AuthService, "_now", lambda self: now)

    await service.login_with_demo_code(DemoLoginRequest(code="TEAM-ALPHA"))
    await service.login_with_demo_code(DemoLoginRequest(code="Team Alpha"))

    users_result = await auth_session.execute(select(User))
    users = users_result.scalars().all()
    assert len(users) == 2
    assert {user.account_type for user in users} == {"demo"}
    assert {user.demo_code for user in users} == {"TEAM-ALPHA", "Team Alpha"}
    emails = {user.email for user in users}
    assert len(emails) == 2


@pytest.mark.asyncio
async def test_multiple_oauth_sessions_allowed(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(AuthService, "_now", lambda self: now)

    identity = OAuth2Identity(subject="id-1", email="limit@example.com", name=None)
    await service.create_session_from_oauth(identity)
    await service.create_session_from_oauth(identity)

    tokens_result = await auth_session.execute(select(RefreshToken))
    tokens = tokens_result.scalars().all()
    assert len(tokens) == 2
    assert all(token.revoked_at is None for token in tokens)


@pytest.mark.asyncio
async def test_register_user_creates_pending_account(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry)

    monkeypatch.setattr(AuthService, "_now", lambda self: datetime.now(timezone.utc))

    payload = RegistrationRequest(
        email="new-user@example.com",
        display_name="New User",
        locale="en-US",
        accept_terms=True,
    )

    response = await service.register_user(payload)

    assert response.status == "registered"
    assert response.user_id is not None

    users_result = await auth_session.execute(select(User))
    user = users_result.scalar_one()
    assert user.email == "new-user@example.com"
    assert user.display_name == "New User"
    assert user.locale == "en-US"
    assert user.account_type == "pending"
    assert user.chat_token_quota == 0
    assert user.chat_tokens_remaining == 0


@pytest.mark.asyncio
async def test_register_user_returns_existing_status(
    auth_session: AsyncSession,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry)

    user = User(
        email="existing@example.com",
        display_name="Existing User",
        locale="zh-CN",
        account_type="email",
    )
    auth_session.add(user)
    await auth_session.flush()

    payload = RegistrationRequest(
        email="existing@example.com",
        display_name="Updated Name",
        locale="en-US",
        accept_terms=True,
    )

    response = await service.register_user(payload)

    assert response.status == "existing"
    users_result = await auth_session.execute(select(User))
    stored = users_result.scalar_one()
    assert stored.display_name == "Updated Name"
    assert stored.locale == "en-US"


@pytest.mark.asyncio
async def test_oauth_login_preserves_chat_tokens_when_exhausted(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry, default_chat_quota=3)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(AuthService, "_now", lambda self: now)

    identity = OAuth2Identity(subject="quota-user", email="quota@example.com", name=None)
    await service.create_session_from_oauth(identity)

    user_result = await auth_session.execute(select(User))
    user = user_result.scalar_one()
    assert user.chat_tokens_remaining == 3

    user.chat_tokens_remaining = 0
    await auth_session.flush()

    await service.create_session_from_oauth(identity, session_id="second")

    refreshed_user = (await auth_session.execute(select(User))).scalar_one()
    assert refreshed_user.chat_token_quota == 3
    assert refreshed_user.chat_tokens_remaining == 0


@pytest.mark.asyncio
async def test_refresh_token_revokes_previous_token(
    auth_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = StubDemoRegistry()
    service = make_auth_service(auth_session, registry)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(AuthService, "_now", lambda self: now)

    identity = OAuth2Identity(subject="refresh-1", email="refresh@example.com", name=None)
    tokens = await service.create_session_from_oauth(identity)

    refresh_payload = TokenRefreshRequest(refresh_token=tokens.refresh_token)
    refreshed = await service.refresh_token(refresh_payload)

    assert refreshed.access_token != tokens.access_token

    token_rows = await auth_session.execute(select(RefreshToken))
    all_tokens = token_rows.scalars().all()
    assert len(all_tokens) == 2
    revoked = [token for token in all_tokens if token.revoked_at is not None]
    assert len(revoked) == 1
