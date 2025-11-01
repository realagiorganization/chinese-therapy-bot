from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    """Payload accepted when recording a product analytics event."""

    event_type: str = Field(..., max_length=64)
    user_id: UUID | None = None
    session_id: UUID | None = None
    funnel_stage: str | None = Field(default=None, max_length=32)
    properties: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class AnalyticsEventResponse(BaseModel):
    """Response returned after recording an event."""

    id: UUID
    created_at: datetime


class JourneyEngagementMetrics(BaseModel):
    """Key engagement signals for the therapy journey experience."""

    active_users: int
    chat_turns: int
    avg_messages_per_session: float
    therapist_profile_views: int
    therapist_conversion_rate: float
    summary_views: int
    journey_report_views: int


class ConversionMetrics(BaseModel):
    """High-level conversion funnel metrics."""

    signup_started: int
    signup_completed: int
    signup_completion_rate: float
    therapist_profile_views: int
    therapist_connect_clicks: int
    therapist_connect_rate: float


class AnalyticsSummary(BaseModel):
    """Aggregated analytics snapshot for a time window."""

    window_start: datetime
    window_end: datetime
    engagement: JourneyEngagementMetrics
    conversion: ConversionMetrics
