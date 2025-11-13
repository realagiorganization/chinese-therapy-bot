from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import ssl
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.util import immutabledict

from app.core.config import get_settings
from app.core.migrations import migrate_database


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def prepare_engine_arguments(database_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize the URL and translate sslmode for asyncpg engines."""
    url = make_url(database_url)
    drivername = url.drivername or ""
    if "asyncpg" not in drivername:
        return database_url, {}

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    connect_args: dict[str, Any] = {}

    if sslmode:
        ssl_value = _sslmode_to_asyncpg_ssl(sslmode)
        if ssl_value is not None:
            connect_args["ssl"] = ssl_value

    sanitized_url = url.set(query=immutabledict(query))
    return str(sanitized_url), connect_args


def _sslmode_to_asyncpg_ssl(sslmode: str) -> Any:
    """Map libpq-style sslmode to asyncpg ssl argument."""
    normalized = sslmode.lower()
    if normalized == "disable":
        return False
    if normalized in {"allow", "prefer"}:
        return None
    if normalized in {"require", "verify-full"}:
        return True
    if normalized == "verify-ca":
        context = ssl.create_default_context()
        context.check_hostname = False
        return context

    raise ValueError(f"Unsupported sslmode '{sslmode}' for asyncpg.")


def _init_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    database_url, connect_args = prepare_engine_arguments(settings.database_url)
    engine_kwargs: dict[str, Any] = {"future": True}
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    engine = create_async_engine(database_url, **engine_kwargs)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None or _session_factory is None:
        _engine, _session_factory = _init_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _engine is None or _session_factory is None:
        _engine, _session_factory = _init_engine()
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_database() -> None:
    """Ensure the database schema is up to date via Alembic migrations."""
    # Initialize engine so session factory is ready for subsequent usage.
    get_engine()
    await migrate_database()
