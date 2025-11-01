from datetime import date, datetime

from pydantic import BaseModel, Field


class DailyReport(BaseModel):
    report_date: date
    title: str
    spotlight: str
    summary: str
    mood_delta: int = Field(default=0, description="Change in self-reported mood score.")


class WeeklyReport(BaseModel):
    week_start: date
    themes: list[str]
    highlights: str
    action_items: list[str]
    risk_level: str = Field(default="low")


class JourneyReportsResponse(BaseModel):
    daily: list[DailyReport]
    weekly: list[WeeklyReport]
    conversations: list["ConversationSlice"] = Field(
        default_factory=list,
        description="Recent chat sessions with limited message history for context.",
    )


class ConversationMessage(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime


class ConversationSlice(BaseModel):
    session_id: str
    started_at: datetime
    updated_at: datetime
    therapist_id: str | None = None
    messages: list[ConversationMessage] = Field(default_factory=list)


JourneyReportsResponse.model_rebuild()
