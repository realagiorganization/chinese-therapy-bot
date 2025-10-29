from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.reports import ReportsService
from app.services.therapists import TherapistService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_auth_service() -> AuthService:
    """Provide AuthService instance."""
    return AuthService()


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChatService:
    """Provide ChatService instance."""
    return ChatService(session)


async def get_therapist_service(
    session: AsyncSession = Depends(get_db_session),
) -> TherapistService:
    """Provide TherapistService instance."""
    return TherapistService(session)


async def get_reports_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReportsService:
    """Provide ReportsService instance."""
    return ReportsService(session)
