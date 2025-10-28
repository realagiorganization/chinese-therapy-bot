from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.reports import ReportsService
from app.services.therapists import TherapistService


def get_auth_service() -> AuthService:
    """Provide AuthService instance."""
    return AuthService()


def get_chat_service() -> ChatService:
    """Provide ChatService instance."""
    return ChatService()


def get_therapist_service() -> TherapistService:
    """Provide TherapistService instance."""
    return TherapistService()


def get_reports_service() -> ReportsService:
    """Provide ReportsService instance."""
    return ReportsService()
