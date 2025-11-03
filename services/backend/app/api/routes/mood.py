from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_mood_service
from app.schemas.mood import (
    MoodCheckInCreate,
    MoodCheckInItem,
    MoodCheckInListResponse,
    MoodSummaryItem,
)
from app.services.mood import MoodService


router = APIRouter()


@router.post(
    "/{user_id}/check-ins",
    response_model=MoodCheckInItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new mood check-in for a user.",
)
async def create_mood_check_in(
    user_id: str,
    payload: MoodCheckInCreate,
    service: MoodService = Depends(get_mood_service),
) -> MoodCheckInItem:
    try:
        record = await service.create_check_in(
            user_id,
            score=payload.score,
            energy_level=payload.energy_level,
            emotion=payload.emotion,
            tags=payload.tags,
            note=payload.note,
            context=payload.context,
            check_in_at=payload.check_in_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MoodCheckInItem.model_validate(record)


@router.get(
    "/{user_id}/check-ins",
    response_model=MoodCheckInListResponse,
    summary="List recent mood check-ins alongside summary metrics.",
)
async def list_mood_check_ins(
    user_id: str,
    limit: int = Query(
        30,
        ge=1,
        le=100,
        description="Maximum number of historical check-ins to return.",
    ),
    window_days: int = Query(
        14,
        ge=1,
        le=90,
        description="Trailing window used for summary analytics (days).",
    ),
    service: MoodService = Depends(get_mood_service),
) -> MoodCheckInListResponse:
    try:
        records = await service.list_check_ins(user_id, limit=limit)
        summary = await service.summarize(user_id, window_days=window_days)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    items = [MoodCheckInItem.model_validate(record) for record in records]
    return MoodCheckInListResponse(
        items=items,
        summary=MoodSummaryItem.from_domain(summary),
    )


@router.get(
    "/{user_id}/summary",
    response_model=MoodSummaryItem,
    summary="Retrieve mood summary metrics for a user.",
)
async def get_mood_summary(
    user_id: str,
    window_days: int = Query(
        14,
        ge=1,
        le=90,
        description="Trailing window used for summary analytics (days).",
    ),
    service: MoodService = Depends(get_mood_service),
) -> MoodSummaryItem:
    try:
        summary = await service.summarize(user_id, window_days=window_days)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MoodSummaryItem.from_domain(summary)
