from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.asr import AzureSpeechTranscriber
from app.integrations.embeddings import EmbeddingClient
from app.integrations.google import GoogleOAuthClient
from app.integrations.llm import ChatOrchestrator
from app.integrations.sms import ConsoleSMSProvider
from app.integrations.storage import ChatTranscriptStorage
from app.integrations.therapists import TherapistDataStorage
from app.services.asr import AutomaticSpeechRecognitionService
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.evaluation import ResponseEvaluator
from app.services.feature_flags import FeatureFlagService
from app.services.language_detection import LanguageDetector
from app.services.memory import ConversationMemoryService
from app.services.recommendations import TherapistRecommendationService
from app.services.reports import ReportsService
from app.services.templates import ChatTemplateService
from app.services.therapists import TherapistService

_sms_provider: ConsoleSMSProvider | None = None
_google_client: GoogleOAuthClient | None = None
_orchestrator: ChatOrchestrator | None = None
_storage: ChatTranscriptStorage | None = None
_therapist_storage: TherapistDataStorage | None = None
_embedding_client: EmbeddingClient | None = None
_response_evaluator: ResponseEvaluator | None = None
_asr_service: AutomaticSpeechRecognitionService | None = None
_template_service: ChatTemplateService | None = None
_language_detector: LanguageDetector | None = None


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
        global _orchestrator, _storage, _embedding_client, _therapist_storage, _language_detector
        if _orchestrator is None:
            _orchestrator = ChatOrchestrator(settings)
        if _storage is None:
            _storage = ChatTranscriptStorage(settings)
        if _embedding_client is None:
            _embedding_client = EmbeddingClient(settings)
        if _therapist_storage is None:
            _therapist_storage = TherapistDataStorage(settings)
        if _language_detector is None:
            _language_detector = LanguageDetector()

        memory_service = ConversationMemoryService(session, _orchestrator)
        therapist_service = TherapistService(session, storage=_therapist_storage)
        recommendation_service = TherapistRecommendationService(
            session,
            _embedding_client,
            therapist_service=therapist_service,
        )
        return ChatService(
            session,
            _orchestrator,
            _storage,
            memory_service=memory_service,
            recommendation_service=recommendation_service,
            language_detector=_language_detector,
        )


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


async def get_response_evaluator() -> ResponseEvaluator:
    """Provide singleton ResponseEvaluator for guardrail checks."""
    global _response_evaluator
    if _response_evaluator is None:
        _response_evaluator = ResponseEvaluator()
    return _response_evaluator


async def get_asr_service() -> AutomaticSpeechRecognitionService:
    """Provide the AutomaticSpeechRecognitionService singleton."""
    global _asr_service
    if _asr_service is None:
        settings = get_settings()
        try:
            transcriber = AzureSpeechTranscriber(settings)
        except ValueError:
            transcriber = None
        _asr_service = AutomaticSpeechRecognitionService(transcriber)
    return _asr_service


async def get_chat_template_service() -> ChatTemplateService:
    """Provide the ChatTemplateService singleton."""
    global _template_service
    if _template_service is None:
        _template_service = ChatTemplateService()
    return _template_service
