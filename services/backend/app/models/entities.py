from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    """End-user interacting with the therapy chatbot."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, doc="External identity provider ID."
    )
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sessions: Mapped[list[ChatSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("phone_number", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_external_id", "external_id"),
    )


class Therapist(Base):
    """Licensed therapist metadata surfaced to the user."""

    __tablename__ = "therapists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(120))
    specialties: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    languages: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    price_per_session: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    availability: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sessions: Mapped[list[ChatSession]] = relationship(back_populates="therapist")
    localizations: Mapped[list["TherapistLocalization"]] = relationship(
        back_populates="therapist", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    """Conversation session between user and chatbot."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("therapists.id", ondelete="set null"), nullable=True
    )
    session_state: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[User] = relationship(back_populates="sessions")
    therapist: Mapped[Therapist | None] = relationship(back_populates="sessions")
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

    __table_args__ = (
        Index("ix_chat_sessions_user", "user_id", postgresql_using="btree"),
    )


class ChatMessage(Base):
    """Individual messages exchanged in a chat session."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="cascade"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    sequence_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_idx", "session_id", "sequence_index"),
    )


class DailySummary(Base):
    """Daily reflection generated by summary agents."""

    __tablename__ = "daily_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    spotlight: Mapped[str] = mapped_column(String(280))
    summary: Mapped[str] = mapped_column(Text)
    mood_delta: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "summary_date", name="uq_daily_summary_day"),
        Index("ix_daily_summaries_user", "user_id"),
    )


class WeeklySummary(Base):
    """Weekly compilation of therapy journey insights."""

    __tablename__ = "weekly_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    themes: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    highlights: Mapped[str] = mapped_column(Text)
    action_items: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_summary_week"),
        Index("ix_weekly_summaries_user", "user_id"),
    )


class ConversationMemory(Base):
    """Long-lived conversation memory slices derived from user messages."""

    __tablename__ = "conversation_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="set null"), nullable=True
    )
    keywords: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    summary: Mapped[str] = mapped_column(Text)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_conversation_memory_session"),
        Index("ix_conversation_memories_user", "user_id"),
        Index("ix_conversation_memories_keywords", "keywords", postgresql_using="gin"),
    )


class LoginChallenge(Base):
    """Authentication challenge for SMS OTP or third-party flows."""

    __tablename__ = "login_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        Index("ix_login_challenges_phone", "phone_number"),
        Index("ix_login_challenges_provider", "provider"),
    )


class RefreshToken(Base):
    """Refresh token registry enabling rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user", "user_id"),
    )


class FeatureFlag(Base):
    """Runtime-configurable feature switches."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("rollout_percentage >= 0 AND rollout_percentage <= 100", name="ck_feature_flags_rollout_range"),
    )


class TherapistLocalization(Base):
    """Localized therapist profile values."""

    __tablename__ = "therapist_localizations"

    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("therapists.id", ondelete="cascade"),
        primary_key=True,
    )
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)

    therapist: Mapped[Therapist] = relationship(back_populates="localizations")

    __table_args__ = (
    Index("ix_therapist_localizations_locale", "locale"),
    )


class AnalyticsEvent(Base):
    """Product analytics events captured from user interactions."""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="set null"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="set null"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64))
    funnel_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    user: Mapped[User | None] = relationship("User")
    session: Mapped[ChatSession | None] = relationship("ChatSession")

    __table_args__ = (
        Index("ix_analytics_events_type_time", "event_type", "occurred_at"),
        Index("ix_analytics_events_user_time", "user_id", "occurred_at"),
        Index("ix_analytics_events_stage_time", "funnel_stage", "occurred_at"),
    )


class PilotFeedback(Base):
    """Structured UAT feedback captured during pilot programs."""

    __tablename__ = "pilot_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="set null"),
        nullable=True,
    )
    cohort: Mapped[str] = mapped_column(String(64))
    participant_alias: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="participant")
    channel: Mapped[str] = mapped_column(String(32), default="web")
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment_score: Mapped[int] = mapped_column(Integer, default=3)
    trust_score: Mapped[int] = mapped_column(Integer, default=3)
    usability_score: Mapped[int] = mapped_column(Integer, default=3)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tags: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    highlights: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockers: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", MutableDict.as_mutable(JSON), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        Index("ix_pilot_feedback_cohort", "cohort"),
        Index("ix_pilot_feedback_channel", "channel"),
        Index("ix_pilot_feedback_role", "role"),
        Index("ix_pilot_feedback_submitted_at", "submitted_at"),
    )


class PilotCohortParticipant(Base):
    """Pilot cohort participant roster used to manage recruitment and engagement."""

    __tablename__ = "pilot_cohort_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cohort: Mapped[str] = mapped_column(String(64))
    participant_alias: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), default="web")
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")
    status: Mapped[str] = mapped_column(String(24), default="invited")
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    invite_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_received: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", MutableDict.as_mutable(JSON), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("cohort", "contact_email", name="uq_pilot_cohort_email"),
        UniqueConstraint("cohort", "contact_phone", name="uq_pilot_cohort_phone"),
        Index("ix_pilot_cohort_participants_cohort", "cohort"),
        Index("ix_pilot_cohort_participants_status", "status"),
        Index("ix_pilot_cohort_participants_channel", "channel"),
    )
