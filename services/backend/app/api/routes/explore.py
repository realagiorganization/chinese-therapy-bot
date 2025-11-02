from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.schemas.explore import ExploreModulesResponse
from app.services.explore import ExploreService
from app.services.feature_flags import FeatureFlagService
from app.services.reports import ReportsService


router = APIRouter()


@router.get(
    "/modules",
    response_model=ExploreModulesResponse,
    status_code=status.HTTP_200_OK,
    summary="Return Explore page modules tailored to the requesting user.",
)
async def list_explore_modules(
    user_id: str = Query(..., alias="userId", description="User identifier for personalization."),
    locale: str = Query("zh-CN", description="Preferred locale for localized content."),
    session: AsyncSession = Depends(get_db_session),
) -> ExploreModulesResponse:
    settings = get_settings()
    feature_flags = FeatureFlagService(session, settings)
    reports_service = ReportsService(session)
    explore_service = ExploreService(feature_flags, reports_service)
    return await explore_service.build_modules(user_id=user_id, locale=locale)
