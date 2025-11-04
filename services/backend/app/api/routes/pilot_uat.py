from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_pilot_uat_service
from app.schemas.pilot_uat import (
    PilotUATBacklogResponse,
    PilotUATSessionCreate,
    PilotUATSessionFilters,
    PilotUATSessionListResponse,
    PilotUATSessionResponse,
    PilotUATSessionSummary,
)
from app.services.pilot_uat import PilotUATService

router = APIRouter()


@router.post(
    "/sessions",
    response_model=PilotUATSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_pilot_uat_session(
    payload: PilotUATSessionCreate,
    service: PilotUATService = Depends(get_pilot_uat_service),
) -> PilotUATSessionResponse:
    """Persist a pilot UAT session log entry."""
    return await service.log_session(payload)


@router.get(
    "/sessions",
    response_model=PilotUATSessionListResponse,
)
async def list_pilot_uat_sessions(
    cohort: str | None = None,
    participant_id: str | None = None,
    participant_alias: str | None = None,
    platform: str | None = None,
    environment: str | None = None,
    facilitator: str | None = None,
    scenario: str | None = None,
    occurred_after: str | None = Query(default=None, description="ISO8601 timestamp filter."),
    occurred_before: str | None = Query(default=None, description="ISO8601 timestamp filter."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: PilotUATService = Depends(get_pilot_uat_service),
) -> PilotUATSessionListResponse:
    """List recorded UAT sessions using optional filters."""
    filters = PilotUATSessionFilters(
        cohort=cohort,
        participant_id=participant_id,  # type: ignore[arg-type]
        participant_alias=participant_alias,
        platform=platform,
        environment=environment,
        facilitator=facilitator,
        scenario=scenario,
        occurred_after=_parse_datetime(occurred_after),
        occurred_before=_parse_datetime(occurred_before),
    )
    return await service.list_sessions(filters, limit=limit, offset=offset)


@router.get(
    "/sessions/summary",
    response_model=PilotUATSessionSummary,
)
async def summarize_pilot_uat_sessions(
    cohort: str | None = None,
    environment: str | None = None,
    service: PilotUATService = Depends(get_pilot_uat_service),
) -> PilotUATSessionSummary:
    """Return aggregated metrics for recorded UAT sessions."""
    filters = PilotUATSessionFilters(cohort=cohort, environment=environment)
    return await service.summarize_sessions(filters)


@router.get(
    "/sessions/backlog",
    response_model=PilotUATBacklogResponse,
)
async def prioritize_pilot_uat_backlog(
    cohort: str | None = None,
    environment: str | None = None,
    platform: str | None = None,
    facilitator: str | None = None,
    scenario: str | None = None,
    participant_alias: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    service: PilotUATService = Depends(get_pilot_uat_service),
) -> PilotUATBacklogResponse:
    """Return prioritized backlog entries derived from UAT issues."""
    filters = PilotUATSessionFilters(
        cohort=cohort,
        environment=environment,
        platform=platform,
        facilitator=facilitator,
        scenario=scenario,
        participant_alias=participant_alias,
    )
    return await service.prioritize_backlog(filters, limit=limit)


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise ValueError("Invalid ISO8601 timestamp") from exc
