from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_therapist_service
from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistFilter,
    TherapistImportSummary,
    TherapistListResponse,
    TherapistSyncRequest,
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
    locale: str = "zh-CN",
    recommended: bool | None = None,
    service: TherapistService = Depends(get_therapist_service),
) -> TherapistListResponse:
    filters = TherapistFilter(
        specialty=specialty,
        language=language,
        price_max=price_max,
        locale=locale,
        is_recommended=recommended,
    )
    return await service.list_therapists(filters)


@router.get(
    "/{therapist_id}",
    response_model=TherapistDetailResponse,
    summary="Fetch therapist details.",
)
async def get_therapist(
    therapist_id: str,
    locale: str = "zh-CN",
    service: TherapistService = Depends(get_therapist_service),
) -> TherapistDetailResponse:
    try:
        return await service.get_therapist(therapist_id, locale=locale)
    except ValueError as exc:  # pragma: no cover - placeholder for future error handling
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/admin/import",
    response_model=TherapistImportSummary,
    summary="Import therapist profiles from configured storage.",
)
async def import_therapists(
    request: TherapistSyncRequest,
    service: TherapistService = Depends(get_therapist_service),
) -> TherapistImportSummary:
    try:
        return await service.sync_from_storage(
            prefix=request.prefix,
            locales=request.locales,
            dry_run=request.dry_run,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
