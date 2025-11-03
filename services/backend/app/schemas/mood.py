from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.mood import MoodSummary, MoodTrendPoint


class MoodCheckInCreate(BaseModel):
    """Payload to record a new mood check-in."""

    score: int = Field(..., ge=1, le=5, description="Mood score from 1 (low) to 5 (high).")
    energy_level: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Optional energy level rating aligned to the 1-5 scale.",
    )
    emotion: str | None = Field(default=None, description="Optional primary emotion keyword.")
    tags: list[str] | None = Field(
        default=None,
        description="Optional set of tags describing the check-in context.",
    )
    note: str | None = Field(default=None, description="Free-form reflection notes.")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Structured metadata captured by clients (e.g., triggers).",
    )
    check_in_at: datetime | None = Field(
        default=None,
        description="Timestamp when the check-in occurred; defaults to now in the user's timezone.",
    )


class MoodCheckInItem(BaseModel):
    """Serializable view of a mood check-in record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    score: int
    energy_level: int | None = None
    emotion: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    context: dict[str, Any] | None = None
    check_in_at: datetime
    created_at: datetime
    updated_at: datetime


class MoodTrendPointItem(BaseModel):
    """Aggregated score snapshot for a date."""

    date: date
    average_score: float
    sample_count: int

    @classmethod
    def from_domain(cls, point: MoodTrendPoint) -> "MoodTrendPointItem":
        return cls(
            date=point.date,
            average_score=point.average_score,
            sample_count=point.sample_count,
        )


class MoodSummaryItem(BaseModel):
    """Summary metrics over a trailing window of check-ins."""

    average_score: float = Field(..., ge=0)
    sample_count: int = Field(..., ge=0)
    streak_days: int = Field(..., ge=0)
    trend: list[MoodTrendPointItem]
    last_check_in: MoodCheckInItem | None = None

    @classmethod
    def from_domain(cls, summary: MoodSummary) -> "MoodSummaryItem":
        return cls(
            average_score=summary.average_score,
            sample_count=summary.sample_count,
            streak_days=summary.streak_days,
            trend=[MoodTrendPointItem.from_domain(point) for point in summary.trend],
            last_check_in=(
                MoodCheckInItem.model_validate(summary.last_check_in)
                if summary.last_check_in
                else None
            ),
        )


class MoodCheckInListResponse(BaseModel):
    """API payload combining recent check-ins and summary metrics."""

    items: list[MoodCheckInItem]
    summary: MoodSummaryItem
