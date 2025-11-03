from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_feedback_service, get_pilot_participant_service
from app.schemas.feedback import (
    PilotBacklogResponse,
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantItem,
    PilotParticipantListResponse,
    PilotParticipantUpdate,
    PilotParticipantSummary,
)
from app.services.feedback import PilotFeedbackService, PilotParticipantService

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
        minimum_trust_score=minimum_trust_score,
    )
    return await service.list_feedback(filters, limit=limit, offset=offset)


@router.get(
    "/pilot/backlog",
    response_model=PilotBacklogResponse,
    summary="Aggregate pilot feedback into a prioritized backlog view.",
)
async def get_pilot_backlog(
    cohort: str | None = Query(default=None, description="Filter items by pilot cohort tag."),
    channel: str | None = Query(default=None, description="Filter by primary feedback channel."),
    role: str | None = Query(default=None, description="Filter by participant role."),
    minimum_trust_score: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Minimum trust score inclusive filter (1-5).",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of backlog items to return.",
    ),
    service: PilotFeedbackService = Depends(get_feedback_service),
) -> PilotBacklogResponse:
    filters = PilotFeedbackFilters(
        cohort=cohort,
        channel=channel,
        role=role,
        minimum_trust_score=minimum_trust_score,
    )
    return await service.generate_backlog(filters, limit=limit)


@router.post(
    "/pilot/participants",
    response_model=PilotParticipantItem,
    status_code=status.HTTP_201_CREATED,
    summary="Register or invite a pilot cohort participant.",
)
async def create_pilot_participant(
    payload: PilotParticipantCreate,
    service: PilotParticipantService = Depends(get_pilot_participant_service),
) -> PilotParticipantItem:
    try:
        return await service.create_participant(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/pilot/participants",
    response_model=PilotParticipantListResponse,
    summary="List pilot participants and filter by engagement status.",
)
async def list_pilot_participants(
    cohort: str | None = Query(default=None, description="Filter participants by cohort slug."),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by participant status."),
    requires_follow_up: bool | None = Query(
        default=None,
        description="Return only participants requiring follow-up when true.",
    ),
    tag: str | None = Query(default=None, description="Return participants tagged with the supplied label."),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of participant records to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        le=1000,
        description="Number of participant records to skip for pagination.",
    ),
    service: PilotParticipantService = Depends(get_pilot_participant_service),
) -> PilotParticipantListResponse:
    filters = PilotParticipantFilters(
        cohort=cohort,
        status=status_filter,
        requires_follow_up=requires_follow_up,
        tag=tag,
    )
    return await service.list_participants(filters, limit=limit, offset=offset)


@router.get(
    "/pilot/participants/summary",
    response_model=PilotParticipantSummary,
    summary="Summarize pilot participant recruitment and follow-up state.",
)
async def summarize_pilot_participants(
    cohort: str | None = Query(default=None, description="Optional cohort filter."),
    status_filter: str | None = Query(default=None, alias="status", description="Optional status filter."),
    requires_follow_up: bool | None = Query(
        default=None, description="When true, only consider participants requiring follow-up."
    ),
    tag: str | None = Query(default=None, description="Filter to participants tagged with the supplied label."),
    service: PilotParticipantService = Depends(get_pilot_participant_service),
) -> PilotParticipantSummary:
    filters = PilotParticipantFilters(
        cohort=cohort,
        status=status_filter,
        requires_follow_up=requires_follow_up,
        tag=tag,
    )
    return await service.summarize_participants(filters)


@router.patch(
    "/pilot/participants/{participant_id}",
    response_model=PilotParticipantItem,
    summary="Update pilot participant lifecycle state.",
)
async def update_pilot_participant(
    participant_id: UUID,
    payload: PilotParticipantUpdate,
    service: PilotParticipantService = Depends(get_pilot_participant_service),
) -> PilotParticipantItem:
    try:
        return await service.update_participant(participant_id, payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
