from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PilotParticipantStatus(str, Enum):
    """Lifecycle state for a pilot cohort participant."""

    INVITED = "invited"
    CONTACTED = "contacted"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class PilotParticipantBase(BaseModel):
    """Shared fields for pilot cohort participants."""

    cohort: str = Field(..., min_length=1, max_length=64)
    participant_alias: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=32)
    channel: str = Field(default="web", min_length=1, max_length=32)
    locale: str = Field(default="zh-CN", min_length=2, max_length=16)
    status: PilotParticipantStatus = Field(default=PilotParticipantStatus.INVITED)
    source: str | None = Field(default=None, max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=16)
    invite_sent_at: datetime | None = None
    onboarded_at: datetime | None = None
    last_contacted_at: datetime | None = None
    consent_received: bool = False
    notes: str | None = None
    metadata: dict[str, Any] | None = Field(default=None)


class PilotParticipantCreate(PilotParticipantBase):
    """Payload for creating a new pilot cohort participant."""

    pass


class PilotParticipantUpdate(BaseModel):
    """Partial update payload for an existing participant."""

    cohort: str | None = Field(default=None, min_length=1, max_length=64)
    participant_alias: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=32)
    channel: str | None = Field(default=None, min_length=1, max_length=32)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    status: PilotParticipantStatus | None = None
    source: str | None = Field(default=None, max_length=32)
    tags: list[str] | None = Field(default=None, max_length=16)
    invite_sent_at: datetime | None = None
    onboarded_at: datetime | None = None
    last_contacted_at: datetime | None = None
    consent_received: bool | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class PilotParticipantResponse(BaseModel):
    """Serialized representation for API responses."""

    id: UUID
    cohort: str
    participant_alias: str | None
    contact_email: str | None
    contact_phone: str | None
    channel: str
    locale: str
    status: PilotParticipantStatus
    source: str | None
    tags: list[str]
    invite_sent_at: datetime | None
    onboarded_at: datetime | None
    last_contacted_at: datetime | None
    consent_received: bool
    notes: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PilotParticipantFilters(BaseModel):
    """Optional filters when listing participants."""

    cohort: str | None = None
    status: PilotParticipantStatus | None = None
    channel: str | None = None
    source: str | None = None
    consent_received: bool | None = None
    search: str | None = Field(default=None, max_length=64)


class PilotParticipantListResponse(BaseModel):
    """Paginated participant listings."""

    total: int
    items: list[PilotParticipantResponse]


class FollowUpUrgency(str, Enum):
    """Indicates how soon a follow-up action should occur."""

    UPCOMING = "upcoming"
    DUE = "due"
    OVERDUE = "overdue"


class PilotFollowUp(BaseModel):
    """Recommended next action for a pilot participant engagement."""

    participant_id: UUID
    cohort: str
    participant_alias: str | None
    channel: str
    locale: str
    status: PilotParticipantStatus
    due_at: datetime
    urgency: FollowUpUrgency
    reason: str
    subject: str
    message: str


class PilotFollowUpList(BaseModel):
    """Collection of follow-up recommendations."""

    generated_at: datetime
    total: int
    items: list[PilotFollowUp]
