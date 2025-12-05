from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, conint


class PilotFeedbackCreate(BaseModel):
    """Payload for recording pilot UAT feedback."""

    cohort: str = Field(..., min_length=1, max_length=64)
    role: str = Field(default="participant", min_length=1, max_length=32)
    channel: str = Field(default="web", min_length=1, max_length=32)
    scenario: str | None = Field(default=None, max_length=64)
    participant_alias: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
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
    severity: str | None = None
    follow_up_needed: bool | None = None
    submitted_since: datetime | None = None
    submitted_until: datetime | None = None
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


class PilotFeedbackTagStat(BaseModel):
    """Frequency breakdown for a feedback tag."""

    tag: str
    count: int


class PilotFeedbackScorecard(BaseModel):
    """Aggregated pilot feedback score averages."""

    average_sentiment: float
    average_trust: float
    average_usability: float
    tone_support_rate: float
    trust_confidence_rate: float
    usability_success_rate: float


class PilotFeedbackInsight(BaseModel):
    """Recent highlight/blocker excerpt."""

    cohort: str
    role: str
    channel: str
    scenario: str | None
    participant_alias: str | None
    sentiment_score: int
    trust_score: int
    usability_score: int
    severity: str | None
    tags: list[str]
    highlights: str | None
    blockers: str | None
    follow_up_needed: bool
    submitted_at: datetime


class PilotFeedbackReport(BaseModel):
    """Aggregated view of pilot feedback metrics."""

    generated_at: datetime
    total_entries: int
    filters: PilotFeedbackFilters
    average_scores: PilotFeedbackScorecard
    severity_breakdown: dict[str, int]
    channel_breakdown: dict[str, int]
    role_breakdown: dict[str, int]
    tag_frequency: list[PilotFeedbackTagStat]
    follow_up_required: int
    recent_highlights: list[PilotFeedbackInsight]
    blocker_insights: list[PilotFeedbackInsight]
