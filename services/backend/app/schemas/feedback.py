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


class PilotFeedbackTagSummary(BaseModel):
    """Aggregated tag frequency across pilot feedback entries."""

    tag: str
    count: int


class PilotFeedbackGroupSummary(BaseModel):
    """Aggregated score metrics for a specific cohort/channel/role grouping."""

    key: str
    total: int
    average_sentiment: float | None
    average_trust: float | None
    average_usability: float | None
    follow_up_needed: int


class PilotFeedbackSummary(BaseModel):
    """High-level aggregation of pilot feedback sentiment and themes."""

    total_entries: int
    average_sentiment: float | None
    average_trust: float | None
    average_usability: float | None
    follow_up_needed: int
    top_tags: list[PilotFeedbackTagSummary]
    by_cohort: list[PilotFeedbackGroupSummary]
    by_channel: list[PilotFeedbackGroupSummary]
    by_role: list[PilotFeedbackGroupSummary]
