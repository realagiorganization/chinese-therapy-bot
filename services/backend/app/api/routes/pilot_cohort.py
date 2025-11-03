from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_pilot_cohort_service
from app.schemas.pilot_cohort import (
    PilotFollowUpList,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantListResponse,
    PilotParticipantResponse,
    PilotParticipantStatus,
    PilotParticipantUpdate,
)
from app.services.pilot_cohort import PilotCohortService


router = APIRouter()


@router.post(
    "/participants",
    status_code=status.HTTP_201_CREATED,
    response_model=PilotParticipantResponse,
    summary="Create a new pilot cohort participant entry.",
)
async def create_pilot_participant(
    payload: PilotParticipantCreate,
    service: PilotCohortService = Depends(get_pilot_cohort_service),
) -> PilotParticipantResponse:
    participant = await service.create_participant(payload)
    return service.as_response(participant)


@router.get(
    "/participants",
    response_model=PilotParticipantListResponse,
    summary="List pilot cohort participants with optional filters.",
)
async def list_pilot_participants(
    cohort: str | None = Query(default=None, description="Filter by cohort identifier."),
    status: PilotParticipantStatus | None = Query(default=None, description="Filter by participant status."),
    channel: str | None = Query(default=None, description="Filter by preferred channel."),
    source: str | None = Query(default=None, description="Filter by acquisition source."),
    consent_received: bool | None = Query(
        default=None,
        description="Filter by consent acknowledgement.",
    ),
    search: str | None = Query(
        default=None,
        description="Case-insensitive search across alias/email/phone.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of participants to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        le=1000,
        description="Number of records to skip.",
    ),
    service: PilotCohortService = Depends(get_pilot_cohort_service),
) -> PilotParticipantListResponse:
    filters = PilotParticipantFilters(
        cohort=cohort,
        status=status,
        channel=channel,
        source=source,
        consent_received=consent_received,
        search=search,
    )
    return await service.list_participants(filters, limit=limit, offset=offset)


@router.get(
    "/participants/followups",
    response_model=PilotFollowUpList,
    summary="Generate follow-up recommendations for pilot engagement.",
)
async def plan_pilot_followups(
    cohort: str | None = Query(default=None, description="Filter by cohort identifier."),
    status: PilotParticipantStatus | None = Query(
        default=None,
        description="Optional participant status filter applied before computing follow-ups.",
    ),
    channel: str | None = Query(default=None, description="Filter by preferred channel."),
    horizon_days: int = Query(
        default=7,
        ge=1,
        le=30,
        description="Include follow-ups that fall within the next N days (default: 7).",
    ),
    service: PilotCohortService = Depends(get_pilot_cohort_service),
) -> PilotFollowUpList:
    filters = PilotParticipantFilters(
        cohort=cohort,
        status=status,
        channel=channel,
    )
    return await service.plan_followups(filters, horizon_days=horizon_days)


@router.patch(
    "/participants/{participant_id}",
    response_model=PilotParticipantResponse,
    summary="Update pilot cohort participant details.",
)
async def update_pilot_participant(
    payload: PilotParticipantUpdate,
    service: PilotCohortService = Depends(get_pilot_cohort_service),
    participant_id: UUID = Path(..., description="Participant identifier."),
) -> PilotParticipantResponse:
    participant = await service.update_participant(participant_id, payload)
    return service.as_response(participant)
