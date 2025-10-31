from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.google import GoogleOAuthClient
from app.integrations.llm import ChatOrchestrator
from app.integrations.sms import ConsoleSMSProvider
from app.integrations.storage import ChatTranscriptStorage
from app.integrations.therapists import TherapistDataStorage
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.feature_flags import FeatureFlagService
from app.services.memory import ConversationMemoryService
from app.services.reports import ReportsService
from app.services.therapists import TherapistService

_sms_provider: ConsoleSMSProvider | None = None
_google_client: GoogleOAuthClient | None = None
_orchestrator: ChatOrchestrator | None = None
_storage: ChatTranscriptStorage | None = None
_therapist_storage: TherapistDataStorage | None = None


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


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    """Provide AuthService instance."""
    settings = get_settings()
    global _sms_provider, _google_client
    if _sms_provider is None:
        _sms_provider = ConsoleSMSProvider()
    if _google_client is None:
        _google_client = GoogleOAuthClient(settings)
    return AuthService(
        session=session,
        settings=settings,
        sms_provider=_sms_provider,
        google_client=_google_client,
    )


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChatService:
    """Provide ChatService instance."""
    settings = get_settings()
    global _orchestrator, _storage
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator(settings)
    if _storage is None:
        _storage = ChatTranscriptStorage(settings)
    memory_service = ConversationMemoryService(session, _orchestrator)
    return ChatService(session, _orchestrator, _storage, memory_service=memory_service)


async def get_therapist_service(
    session: AsyncSession = Depends(get_db_session),
) -> TherapistService:
    """Provide TherapistService instance."""
    settings = get_settings()
    global _therapist_storage
    if _therapist_storage is None:
        _therapist_storage = TherapistDataStorage(settings)
    return TherapistService(session, storage=_therapist_storage)


async def get_reports_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReportsService:
    """Provide ReportsService instance."""
    return ReportsService(session)


async def get_feature_flag_service(
    session: AsyncSession = Depends(get_db_session),
) -> FeatureFlagService:
    """Provide FeatureFlagService instance."""
    settings = get_settings()
    return FeatureFlagService(session, settings)


async def get_memory_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationMemoryService:
    """Provide ConversationMemoryService instance for API routes."""
    settings = get_settings()
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator(settings)
    return ConversationMemoryService(session, _orchestrator)
