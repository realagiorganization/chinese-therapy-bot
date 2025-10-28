from datetime import date

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
