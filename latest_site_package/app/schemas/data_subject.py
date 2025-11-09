from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserMatch(BaseModel):
    """Lightweight representation of a user match for SAR tooling."""

    id: UUID
    email: str | None = None
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    external_id: str | None = Field(default=None, alias="externalId")
    display_name: str | None = Field(default=None, alias="displayName")
    locale: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class ExportChatMessage(BaseModel):
    id: UUID
    role: str
    content: str
    sequence_index: int = Field(alias="sequenceIndex")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportChatSession(BaseModel):
    id: UUID
    session_state: str = Field(alias="sessionState")
    started_at: datetime = Field(alias="startedAt")
    updated_at: datetime = Field(alias="updatedAt")
    therapist_id: UUID | None = Field(default=None, alias="therapistId")
    messages: list[ExportChatMessage]

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportDailySummary(BaseModel):
    id: UUID
    summary_date: date = Field(alias="summaryDate")
    title: str
    spotlight: str
    summary: str
    mood_delta: int = Field(alias="moodDelta")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportWeeklySummary(BaseModel):
    id: UUID
    week_start: date = Field(alias="weekStart")
    themes: list[str]
    highlights: str
    action_items: list[str] = Field(alias="actionItems")
    risk_level: str = Field(alias="riskLevel")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportConversationMemory(BaseModel):
    id: UUID
    session_id: UUID | None = Field(default=None, alias="sessionId")
    keywords: list[str]
    summary: str
    last_message_at: datetime = Field(alias="lastMessageAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportAnalyticsEvent(BaseModel):
    id: UUID
    event_type: str = Field(alias="eventType")
    funnel_stage: str | None = Field(default=None, alias="funnelStage")
    occurred_at: datetime = Field(alias="occurredAt")
    properties: dict[str, Any]

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExportUserProfile(BaseModel):
    id: UUID
    email: str | None = None
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    display_name: str | None = Field(default=None, alias="displayName")
    external_id: str | None = Field(default=None, alias="externalId")
    locale: str
    timezone: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class DataSubjectExport(BaseModel):
    user: ExportUserProfile
    sessions: list[ExportChatSession]
    daily_summaries: list[ExportDailySummary] = Field(alias="dailySummaries")
    weekly_summaries: list[ExportWeeklySummary] = Field(alias="weeklySummaries")
    conversation_memories: list[ExportConversationMemory] = Field(
        alias="conversationMemories"
    )
    analytics_events: list[ExportAnalyticsEvent] = Field(alias="analyticsEvents")

    model_config = {"populate_by_name": True}


class DataDeletionReport(BaseModel):
    user_id: UUID = Field(alias="userId")
    messages_redacted: int = Field(alias="messagesRedacted")
    sessions_impacted: int = Field(alias="sessionsImpacted")
    daily_summaries_deleted: int = Field(alias="dailySummariesDeleted")
    weekly_summaries_deleted: int = Field(alias="weeklySummariesDeleted")
    memories_deleted: int = Field(alias="memoriesDeleted")
    analytics_anonymised: int = Field(alias="analyticsAnonymised")
    refresh_tokens_revoked: int = Field(alias="refreshTokensRevoked")
    transcripts_deleted: int = Field(alias="transcriptsDeleted")
    summary_objects_deleted: int = Field(alias="summaryObjectsDeleted")
    pii_fields_cleared: list[str] = Field(alias="piiFieldsCleared")

    model_config = {"populate_by_name": True}
