from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_reports_service
from app.schemas.reports import JourneyReportsResponse
from app.services.reports import ReportsService

router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=JourneyReportsResponse,
    summary="Retrieve latest daily and weekly journey summaries.",
)
async def get_journey_reports(
    user_id: str, service: ReportsService = Depends(get_reports_service)
) -> JourneyReportsResponse:
    try:
        return await service.get_reports(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
