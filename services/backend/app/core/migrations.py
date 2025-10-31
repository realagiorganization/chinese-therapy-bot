from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def _make_alembic_config() -> Config:
    """Return Alembic configuration seeded with runtime paths and database URL."""
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini = project_root / "alembic.ini"
    script_location = project_root / "alembic"

    if not alembic_ini.exists():
        raise RuntimeError(f"Alembic configuration not found at {alembic_ini}")

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured to run migrations.")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


async def migrate_database(revision: str = "head") -> None:
    """Upgrade the database schema to the requested Alembic revision."""
    config = _make_alembic_config()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, config, revision)
