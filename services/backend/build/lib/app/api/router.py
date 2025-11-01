from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    evaluations,
    explore,
    features,
    health,
    memory,
    reports,
    therapists,
    voice,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(therapists.router, prefix="/therapists", tags=["therapists"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(features.router, prefix="/features", tags=["feature-flags"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(explore.router, prefix="/explore", tags=["explore"])
