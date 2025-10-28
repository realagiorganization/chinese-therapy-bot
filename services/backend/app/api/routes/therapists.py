from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_therapist_service
from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistFilter,
    TherapistListResponse,
)
from app.services.therapists import TherapistService

router = APIRouter()


@router.get(
    "/",
    response_model=TherapistListResponse,
    summary="List therapists with optional filters.",
)
async def list_therapists(
    specialty: str | None = None,
    language: str | None = None,
    price_max: float | None = None,
    service: TherapistService = Depends(get_therapist_service),
) -> TherapistListResponse:
    filters = TherapistFilter(
        specialty=specialty,
        language=language,
        price_max=price_max,
    )
    return await service.list_therapists(filters)


@router.get(
    "/{therapist_id}",
    response_model=TherapistDetailResponse,
    summary="Fetch therapist details.",
)
async def get_therapist(
    therapist_id: str, service: TherapistService = Depends(get_therapist_service)
) -> TherapistDetailResponse:
    try:
        return await service.get_therapist(therapist_id)
    except ValueError as exc:  # pragma: no cover - placeholder for future error handling
        raise HTTPException(status_code=404, detail=str(exc)) from exc
