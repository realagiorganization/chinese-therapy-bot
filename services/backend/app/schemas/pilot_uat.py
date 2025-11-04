from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PilotUATIssue(BaseModel):
    """Structured representation for a UAT issue surfaced during a session."""

    title: str = Field(..., min_length=1, max_length=128)
    severity: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=1024)


class PilotUATSessionCreate(BaseModel):
    """Payload for logging a pilot UAT session."""

    cohort: str = Field(..., min_length=1, max_length=64)
    participant_alias: str | None = Field(default=None, max_length=64)
    participant_id: UUID | None = None
    session_date: datetime | None = None
    facilitator: str | None = Field(default=None, max_length=64)
    scenario: str | None = Field(default=None, max_length=64)
    environment: str | None = Field(default=None, max_length=32)
    platform: str | None = Field(default=None, max_length=24)
    device: str | None = Field(default=None, max_length=64)
    satisfaction_score: int = Field(default=3, ge=1, le=5)
    trust_score: int | None = Field(default=None, ge=1, le=5)
    highlights: str | None = Field(default=None, max_length=2000)
    blockers: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    issues: list[PilotUATIssue] = Field(default_factory=list, max_length=32)
    action_items: list[str] = Field(default_factory=list, max_length=32)
    metadata: dict[str, Any] | None = Field(default=None)


class PilotUATSessionResponse(BaseModel):
    """Serialized UAT session returned by the API."""

    id: UUID
    cohort: str
    participant_alias: str | None
    participant_id: UUID | None
    session_date: datetime
    facilitator: str | None
    scenario: str | None
    environment: str | None
    platform: str | None
    device: str | None
    satisfaction_score: int
    trust_score: int | None
    highlights: str | None
    blockers: str | None
    notes: str | None
    issues: list[PilotUATIssue]
    action_items: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PilotUATSessionFilters(BaseModel):
    """Optional filters when listing pilot UAT sessions."""

    cohort: str | None = None
    participant_id: UUID | None = None
    participant_alias: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=24)
    environment: str | None = Field(default=None, max_length=32)
    facilitator: str | None = Field(default=None, max_length=64)
    scenario: str | None = Field(default=None, max_length=64)
    occurred_after: datetime | None = None
    occurred_before: datetime | None = None


class PilotUATSessionListResponse(BaseModel):
    """Paginated list of UAT session entries."""

    total: int
    items: list[PilotUATSessionResponse]


class PilotUATIssueSummary(BaseModel):
    """Aggregated count of issues grouped by severity."""

    severity: str
    count: int


class PilotUATGroupSummary(BaseModel):
    """Aggregate metrics for a grouping dimension."""

    key: str
    total: int
    average_satisfaction: float | None
    average_trust: float | None


class PilotUATSessionSummary(BaseModel):
    """Aggregated view over recorded UAT sessions."""

    total_sessions: int
    distinct_participants: int
    average_satisfaction: float | None
    average_trust: float | None
    sessions_with_blockers: int
    issues_by_severity: list[PilotUATIssueSummary]
    sessions_by_platform: list[PilotUATGroupSummary]
    sessions_by_environment: list[PilotUATGroupSummary]


class PilotUATBacklogItem(BaseModel):
    """Prioritized backlog entry derived from UAT issues/action items."""

    title: str
    severity: str
    occurrences: int
    affected_participants: int
    latest_session_date: datetime
    sample_notes: list[str]
    action_items: list[str]


class PilotUATBacklogResponse(BaseModel):
    """Response payload containing prioritized backlog entries."""

    total: int
    items: list[PilotUATBacklogItem]
