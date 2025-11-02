from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, conint


class PilotParticipantCreate(BaseModel):
    """Payload for registering or inviting a pilot participant."""

    cohort: str = Field(..., min_length=1, max_length=64)
    full_name: str | None = Field(default=None, max_length=120)
    preferred_name: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=32)
    channel: str = Field(default="web", min_length=1, max_length=32)
    locale: str = Field(default="zh-CN", min_length=2, max_length=16)
    timezone: str | None = Field(default=None, max_length=40)
    organization: str | None = Field(default=None, max_length=120)
    status: str = Field(default="prospect", min_length=1, max_length=32)
    requires_follow_up: bool = False
    invited_at: datetime | None = None
    consent_signed_at: datetime | None = None
    onboarded_at: datetime | None = None
    last_contact_at: datetime | None = None
    follow_up_notes: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list, max_length=16)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PilotParticipantUpdate(BaseModel):
    """Subset of fields allowed when updating a pilot participant."""

    full_name: str | None = Field(default=None, max_length=120)
    preferred_name: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=32)
    channel: str | None = Field(default=None, min_length=1, max_length=32)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    timezone: str | None = Field(default=None, max_length=40)
    organization: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    requires_follow_up: bool | None = None
    invited_at: datetime | None = None
    consent_signed_at: datetime | None = None
    onboarded_at: datetime | None = None
    last_contact_at: datetime | None = None
    follow_up_notes: str | None = None
    tags: list[str] | None = Field(default=None, max_length=16)
    metadata: dict[str, Any] | None = None


class PilotParticipantFilters(BaseModel):
    """Query filters for listing pilot participants."""

    cohort: str | None = None
    status: str | None = None
    requires_follow_up: bool | None = None
    tag: str | None = None


class PilotParticipantItem(BaseModel):
    """Serialized representation of a pilot participant."""

    id: UUID
    cohort: str
    full_name: str | None
    preferred_name: str | None
    contact_email: str | None
    contact_phone: str | None
    channel: str
    locale: str
    timezone: str | None
    organization: str | None
    status: str
    requires_follow_up: bool
    invited_at: datetime | None
    consent_signed_at: datetime | None
    onboarded_at: datetime | None
    last_contact_at: datetime | None
    follow_up_notes: str | None
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PilotParticipantListResponse(BaseModel):
    """Collection response when listing pilot participants."""

    total: int
    items: list[PilotParticipantItem]


class PilotFeedbackCreate(BaseModel):
    """Payload for recording pilot UAT feedback."""

    cohort: str = Field(..., min_length=1, max_length=64)
    role: str = Field(default="participant", min_length=1, max_length=32)
    channel: str = Field(default="web", min_length=1, max_length=32)
    scenario: str | None = Field(default=None, max_length=64)
    participant_alias: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    participant_id: UUID | None = None
    sentiment_score: conint(ge=1, le=5) = 3
    trust_score: conint(ge=1, le=5) = 3
    usability_score: conint(ge=1, le=5) = 3
    severity: str | None = Field(default=None, max_length=16)
    tags: list[str] = Field(default_factory=list, max_length=12)
    highlights: str | None = None
    blockers: str | None = None
    follow_up_needed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: UUID | None = None


class PilotFeedbackFilters(BaseModel):
    """Optional filters when listing pilot feedback entries."""

    cohort: str | None = None
    channel: str | None = None
    role: str | None = None
    minimum_trust_score: int | None = Field(default=None, ge=1, le=5)


class PilotFeedbackItem(BaseModel):
    """Serialized pilot feedback entry."""

    id: UUID
    cohort: str
    role: str
    channel: str
    scenario: str | None
    participant_alias: str | None
    contact_email: str | None
    participant_id: UUID | None
    sentiment_score: int
    trust_score: int
    usability_score: int
    severity: str | None
    tags: list[str]
    highlights: str | None
    blockers: str | None
    follow_up_needed: bool
    metadata: dict[str, Any]
    submitted_at: datetime


class PilotFeedbackListResponse(BaseModel):
    """Collection response for pilot feedback listings."""

    total: int
    items: list[PilotFeedbackItem]


class PilotBacklogItem(BaseModel):
    """Aggregated backlog insight derived from pilot feedback."""

    label: str
    cohorts: list[str]
    tag: str | None = None
    scenario: str | None = None
    representative_severity: str | None = None
    frequency: int
    participant_count: int
    follow_up_count: int
    average_sentiment: float
    average_trust: float
    average_usability: float
    priority_score: float
    last_submitted_at: datetime
    highlights: list[str]
    blockers: list[str]


class PilotBacklogResponse(BaseModel):
    """Collection response for prioritized pilot backlog items."""

    total: int
    items: list[PilotBacklogItem]
