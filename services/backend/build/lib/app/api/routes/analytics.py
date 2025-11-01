from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.analytics import AnalyticsEventCreate, AnalyticsEventResponse, AnalyticsSummary
from app.services.analytics import ProductAnalyticsService


router = APIRouter()


@router.post(
    "/events",
    response_model=AnalyticsEventResponse,
    status_code=201,
    summary="Record a product analytics event.",
)
async def record_event(
    payload: AnalyticsEventCreate,
    session: AsyncSession = Depends(get_db_session),
) -> AnalyticsEventResponse:
    service = ProductAnalyticsService(session)
    return await service.record_event(payload)


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Retrieve aggregated analytics metrics.",
)
async def analytics_summary(
    window_hours: int = Query(24, ge=1, le=24 * 14),
    session: AsyncSession = Depends(get_db_session),
) -> AnalyticsSummary:
    service = ProductAnalyticsService(session)
    return await service.summarize(window_hours=window_hours)
