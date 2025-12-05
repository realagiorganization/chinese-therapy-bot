from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_feedback_service
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
    PilotFeedbackReport,
)
from app.services.feedback import PilotFeedbackService

router = APIRouter()


@router.post(
    "/pilot",
    response_model=PilotFeedbackItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record a pilot UAT feedback entry.",
)
async def submit_pilot_feedback(
    payload: PilotFeedbackCreate,
    service: PilotFeedbackService = Depends(get_feedback_service),
) -> PilotFeedbackItem:
    return await service.record_feedback(payload)


@router.get(
    "/pilot",
    response_model=PilotFeedbackListResponse,
    summary="List pilot UAT feedback entries.",
)
async def list_pilot_feedback(
    cohort: str | None = Query(default=None, description="Filter by pilot cohort tag."),
    channel: str | None = Query(default=None, description="Filter by primary channel (web/mobile/etc)."),
    role: str | None = Query(default=None, description="Filter by participant role."),
    severity: str | None = Query(default=None, description="Filter by reported severity (e.g., high/blocker)."),
    follow_up_needed: bool | None = Query(
        default=None, description="Filter entries that require follow-up (true/false)."
    ),
    submitted_since: datetime | None = Query(
        default=None, description="Include entries submitted at or after this ISO timestamp."
    ),
    submitted_until: datetime | None = Query(
        default=None, description="Include entries submitted at or before this ISO timestamp."
    ),
    minimum_trust_score: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Minimum trust score inclusive filter (1-5).",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of records to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        le=1000,
        description="Number of records to skip for pagination.",
    ),
    service: PilotFeedbackService = Depends(get_feedback_service),
) -> PilotFeedbackListResponse:
    filters = PilotFeedbackFilters(
        cohort=cohort,
        channel=channel,
        role=role,
        severity=severity,
        follow_up_needed=follow_up_needed,
        submitted_since=submitted_since,
        submitted_until=submitted_until,
        minimum_trust_score=minimum_trust_score,
    )
    return await service.list_feedback(filters, limit=limit, offset=offset)


@router.get(
    "/pilot/report",
    response_model=PilotFeedbackReport,
    summary="Summarize pilot UAT feedback metrics by cohort or channel.",
)
async def summarize_pilot_feedback(
    cohort: str | None = Query(default=None, description="Filter by pilot cohort tag."),
    channel: str | None = Query(default=None, description="Filter by primary channel (web/mobile/etc)."),
    role: str | None = Query(default=None, description="Filter by participant role."),
    severity: str | None = Query(default=None, description="Filter by reported severity (e.g., high/blocker)."),
    follow_up_needed: bool | None = Query(
        default=None, description="Filter entries that require follow-up (true/false)."
    ),
    submitted_since: datetime | None = Query(
        default=None, description="Include entries submitted at or after this ISO timestamp."
    ),
    submitted_until: datetime | None = Query(
        default=None, description="Include entries submitted at or before this ISO timestamp."
    ),
    minimum_trust_score: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Minimum trust score inclusive filter (1-5).",
    ),
    service: PilotFeedbackService = Depends(get_feedback_service),
) -> PilotFeedbackReport:
    filters = PilotFeedbackFilters(
        cohort=cohort,
        channel=channel,
        role=role,
        severity=severity,
        follow_up_needed=follow_up_needed,
        submitted_since=submitted_since,
        submitted_until=submitted_until,
        minimum_trust_score=minimum_trust_score,
    )
    return await service.summarize_feedback(filters)
