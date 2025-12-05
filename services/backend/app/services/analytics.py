from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsEvent
from app.schemas.analytics import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    AnalyticsSummary,
    ConversionMetrics,
    JourneyEngagementMetrics,
    LocaleEngagementBreakdown,
)


class AnalyticsEventType(str, Enum):
    """Canonical product analytics event identifiers."""

    CHAT_TURN_SENT = "chat_turn_sent"
    SUMMARY_VIEWED = "summary_viewed"
    JOURNEY_REPORT_VIEW = "journey_report_view"
    THERAPIST_PROFILE_VIEW = "therapist_profile_view"
    THERAPIST_CONNECT_CLICK = "therapist_connect_click"
    SIGNUP_STARTED = "signup_started"
    SIGNUP_COMPLETED = "signup_completed"


class ProductAnalyticsService:
    """Records MindWell product analytics events and derives summary metrics."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def record_event(self, payload: AnalyticsEventCreate) -> AnalyticsEventResponse:
        """Persist an analytics event supplied by API consumers."""
        record = await self._create_event(
            event_type=payload.event_type,
            user_id=payload.user_id,
            session_id=payload.session_id,
            funnel_stage=payload.funnel_stage,
            properties=payload.properties,
            occurred_at=payload.occurred_at,
        )
        return AnalyticsEventResponse(id=record.id, created_at=record.created_at)

    async def track_chat_turn(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        locale: str,
        message_length: int,
    ) -> None:
        """Record a chat turn for engagement tracking."""
        await self._create_event(
            event_type=AnalyticsEventType.CHAT_TURN_SENT.value,
            user_id=user_id,
            session_id=session_id,
            funnel_stage="engagement",
            properties={
                "locale": locale,
                "message_length": message_length,
            },
        )

    async def track_therapist_profile_view(
        self,
        *,
        user_id: UUID | None,
        therapist_id: UUID | None,
        locale: str,
    ) -> None:
        """Record a therapist profile view to measure conversion funnels."""
        await self._create_event(
            event_type=AnalyticsEventType.THERAPIST_PROFILE_VIEW.value,
            user_id=user_id,
            funnel_stage="consideration",
            properties={
                "therapist_id": str(therapist_id) if therapist_id else None,
                "locale": locale,
            },
        )

    async def track_therapist_connect_click(
        self,
        *,
        user_id: UUID | None,
        therapist_id: UUID | None,
        locale: str,
        entry_point: str | None = None,
    ) -> None:
        """Record a therapist connect CTA click for conversion tracking."""
        await self._create_event(
            event_type=AnalyticsEventType.THERAPIST_CONNECT_CLICK.value,
            user_id=user_id,
            funnel_stage="conversion",
            properties={
                "therapist_id": str(therapist_id) if therapist_id else None,
                "locale": locale,
                "entry_point": entry_point,
            },
        )

    async def track_journey_report_view(
        self,
        *,
        user_id: UUID,
        report_kind: str,
    ) -> None:
        """Record that the user opened a journey report (daily/weekly/conversation)."""
        await self._create_event(
            event_type=AnalyticsEventType.JOURNEY_REPORT_VIEW.value,
            user_id=user_id,
            funnel_stage="retention",
            properties={"report_kind": report_kind},
        )

    async def track_summary_view(
        self,
        *,
        user_id: UUID,
        summary_type: str,
    ) -> None:
        """Record that the user opened a generated summary."""
        await self._create_event(
            event_type=AnalyticsEventType.SUMMARY_VIEWED.value,
            user_id=user_id,
            funnel_stage="retention",
            properties={"summary_type": summary_type},
        )

    async def track_signup_event(
        self,
        *,
        user_id: UUID | None,
        stage: AnalyticsEventType,
    ) -> None:
        """Record a signup funnel milestone."""
        if stage not in {AnalyticsEventType.SIGNUP_STARTED, AnalyticsEventType.SIGNUP_COMPLETED}:
            raise ValueError("Unsupported signup analytics stage.")

        await self._create_event(
            event_type=stage.value,
            user_id=user_id,
            funnel_stage="activation" if stage is AnalyticsEventType.SIGNUP_STARTED else "conversion",
        )

    async def summarize(
        self,
        *,
        window_hours: int = 24,
        window_end: datetime | None = None,
    ) -> AnalyticsSummary:
        """Aggregate analytics metrics for the requested window."""
        end = self._normalize_datetime(window_end)
        start = end - timedelta(hours=window_hours)
        timeframe_filters = (
            AnalyticsEvent.occurred_at >= start,
            AnalyticsEvent.occurred_at < end,
        )

        event_counts = await self._counts_by_event_type(*timeframe_filters)
        active_users = await self._distinct_user_count(*timeframe_filters)
        chat_sessions = await self._distinct_session_count(
            *timeframe_filters,
            AnalyticsEvent.event_type == AnalyticsEventType.CHAT_TURN_SENT.value,
        )

        chat_turns = event_counts.get(AnalyticsEventType.CHAT_TURN_SENT.value, 0)
        therapist_profile_views = event_counts.get(
            AnalyticsEventType.THERAPIST_PROFILE_VIEW.value, 0
        )
        therapist_connect_clicks = event_counts.get(
            AnalyticsEventType.THERAPIST_CONNECT_CLICK.value, 0
        )
        summary_views = event_counts.get(AnalyticsEventType.SUMMARY_VIEWED.value, 0)
        journey_report_views = event_counts.get(
            AnalyticsEventType.JOURNEY_REPORT_VIEW.value, 0
        )
        signup_started = event_counts.get(AnalyticsEventType.SIGNUP_STARTED.value, 0)
        signup_completed = event_counts.get(AnalyticsEventType.SIGNUP_COMPLETED.value, 0)

        avg_session_messages = (
            float(chat_turns) / chat_sessions if chat_sessions else float(chat_turns)
        )
        therapist_conversion = (
            float(therapist_connect_clicks) / therapist_profile_views
            if therapist_profile_views
            else 0.0
        )
        signup_completion = (
            float(signup_completed) / signup_started if signup_started else 0.0
        )

        engagement = JourneyEngagementMetrics(
            active_users=active_users,
            chat_turns=chat_turns,
            avg_messages_per_session=round(avg_session_messages, 2),
            therapist_profile_views=therapist_profile_views,
            therapist_conversion_rate=round(therapist_conversion, 3),
            summary_views=summary_views,
            journey_report_views=journey_report_views,
        )

        conversion = ConversionMetrics(
            signup_started=signup_started,
            signup_completed=signup_completed,
            signup_completion_rate=round(signup_completion, 3),
            therapist_profile_views=therapist_profile_views,
            therapist_connect_clicks=therapist_connect_clicks,
            therapist_connect_rate=round(therapist_conversion, 3),
        )

        locale_breakdown = await self._locale_breakdown(*timeframe_filters)

        return AnalyticsSummary(
            window_start=start,
            window_end=end,
            engagement=engagement,
            conversion=conversion,
            locale_breakdown=locale_breakdown,
        )

    async def _create_event(
        self,
        *,
        event_type: str,
        user_id: UUID | None,
        session_id: UUID | None = None,
        funnel_stage: str | None = None,
        properties: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> AnalyticsEvent:
        timestamp = self._normalize_datetime(occurred_at)
        record = AnalyticsEvent(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            funnel_stage=funnel_stage,
            properties=properties or {},
            occurred_at=timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def _counts_by_event_type(self, *filters) -> dict[str, int]:
        stmt = (
            select(AnalyticsEvent.event_type, func.count())
            .where(*filters)
            .group_by(AnalyticsEvent.event_type)
        )
        result = await self._session.execute(stmt)
        counts: dict[str, int] = {}
        for event_type, count_value in result.all():
            counts[event_type] = int(count_value or 0)
        return counts

    async def _distinct_user_count(self, *filters) -> int:
        stmt = (
            select(func.count(func.distinct(AnalyticsEvent.user_id)))
            .where(AnalyticsEvent.user_id.isnot(None), *filters)
        )
        result = await self._session.execute(stmt)
        value = result.scalar()
        return int(value or 0)

    async def _distinct_session_count(self, *filters) -> int:
        stmt = (
            select(func.count(func.distinct(AnalyticsEvent.session_id)))
            .where(AnalyticsEvent.session_id.isnot(None), *filters)
        )
        result = await self._session.execute(stmt)
        value = result.scalar()
        return int(value or 0)

    async def _locale_breakdown(
        self,
        *filters,
        limit: int = 5,
    ) -> list[LocaleEngagementBreakdown]:
        event_types = {
            AnalyticsEventType.CHAT_TURN_SENT.value: "chat_turns",
            AnalyticsEventType.THERAPIST_PROFILE_VIEW.value: "therapist_profile_views",
            AnalyticsEventType.THERAPIST_CONNECT_CLICK.value: "therapist_connect_clicks",
        }
        tracked_types = tuple(event_types.keys())
        stmt = (
            select(AnalyticsEvent.event_type, AnalyticsEvent.properties)
            .where(AnalyticsEvent.event_type.in_(tracked_types), *filters)
        )
        result = await self._session.execute(stmt)
        locale_totals: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "chat_turns": 0,
                "therapist_profile_views": 0,
                "therapist_connect_clicks": 0,
            }
        )
        for event_type, properties in result.all():
            locale = (properties or {}).get("locale") or "unknown"
            metric_key = event_types[event_type]
            locale_totals[locale][metric_key] += 1

        breakdown = [
            LocaleEngagementBreakdown(
                locale=locale,
                chat_turns=metrics["chat_turns"],
                therapist_profile_views=metrics["therapist_profile_views"],
                therapist_connect_clicks=metrics["therapist_connect_clicks"],
            )
            for locale, metrics in locale_totals.items()
        ]
        breakdown.sort(
            key=lambda item: (
                item.chat_turns,
                item.therapist_profile_views,
                item.therapist_connect_clicks,
            ),
            reverse=True,
        )
        return breakdown[:limit]

    def _normalize_datetime(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
