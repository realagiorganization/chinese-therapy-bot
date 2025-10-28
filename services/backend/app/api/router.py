from fastapi import APIRouter

from app.api.routes import auth, chat, health, reports, therapists

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(therapists.router, prefix="/therapists", tags=["therapists"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
