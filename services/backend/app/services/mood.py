from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import MoodCheckIn, User


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MoodTrendPoint:
    """Aggregated mood score for a single day."""

    date: date
    average_score: float
    sample_count: int


@dataclass(slots=True)
class MoodSummary:
    """Aggregated statistics for recent mood check-ins."""

    average_score: float
    sample_count: int
    streak_days: int
    trend: list[MoodTrendPoint]
    last_check_in: MoodCheckIn | None

    @classmethod
    def empty(cls) -> "MoodSummary":
        return cls(
            average_score=0.0,
            sample_count=0,
            streak_days=0,
            trend=[],
            last_check_in=None,
        )


class MoodService:
    """Record and analyze user mood check-ins."""

    _DEFAULT_WINDOW_DAYS = 14
    _POSITIVE_THRESHOLD = 3

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_check_in(
        self,
        user_id: str | UUID,
        *,
        score: int,
        energy_level: int | None = None,
        emotion: str | None = None,
        tags: Iterable[str] | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
        check_in_at: datetime | None = None,
    ) -> MoodCheckIn:
        """Persist a new mood check-in for a user."""
        user_uuid = self._coerce_uuid(user_id)
        user = await self._get_or_create_user(user_uuid)

        self._validate_score(score)
        if energy_level is not None:
            self._validate_energy(energy_level)

        tzinfo = self._resolve_timezone(user)
        check_in_timestamp = self._normalize_timestamp(check_in_at, tzinfo)

        record = MoodCheckIn(
            id=uuid4(),
            user_id=user.id,
            score=score,
            energy_level=energy_level,
            emotion=self._normalize_text(emotion),
            tags=self._normalize_tags(tags),
            note=self._normalize_text(note),
            context=dict(context) if context else None,
            check_in_at=check_in_timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_check_ins(
        self,
        user_id: str | UUID,
        *,
        limit: int = 30,
    ) -> list[MoodCheckIn]:
        """Return recent mood check-ins sorted by recency."""
        user_uuid = self._coerce_uuid(user_id)
        stmt = (
            select(MoodCheckIn)
            .where(MoodCheckIn.user_id == user_uuid)
            .order_by(MoodCheckIn.check_in_at.desc())
            .limit(max(1, limit))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def summarize(
        self,
        user_id: str | UUID,
        *,
        window_days: int | None = None,
    ) -> MoodSummary:
        """Compute mood summary statistics over a trailing window."""
        user_uuid = self._coerce_uuid(user_id)
        user = await self._session.get(User, user_uuid)
        if not user:
            return MoodSummary.empty()

        window = max(1, window_days or self._DEFAULT_WINDOW_DAYS)
        now_utc = datetime.now(timezone.utc)
        window_start = (now_utc - timedelta(days=window - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        stmt = (
            select(MoodCheckIn)
            .where(MoodCheckIn.user_id == user_uuid)
            .where(MoodCheckIn.check_in_at >= window_start)
            .order_by(MoodCheckIn.check_in_at.desc())
        )
        result = await self._session.execute(stmt)
        window_records = list(result.scalars().all())

        latest_stmt = (
            select(MoodCheckIn)
            .where(MoodCheckIn.user_id == user_uuid)
            .order_by(MoodCheckIn.check_in_at.desc())
            .limit(1)
        )
        latest_result = await self._session.execute(latest_stmt)
        latest_check_in = latest_result.scalar_one_or_none()

        if not window_records:
            summary = MoodSummary.empty()
            summary.last_check_in = latest_check_in
            return summary

        tzinfo = self._resolve_timezone(user)
        average_score = sum(record.score for record in window_records) / len(window_records)
        trend_map = self._aggregate_daily_scores(window_records, tzinfo)
        trend_points = self._build_trend_points(trend_map)
        streak_days = self._compute_streak(trend_map)

        return MoodSummary(
            average_score=round(average_score, 2),
            sample_count=len(window_records),
            streak_days=streak_days,
            trend=trend_points,
            last_check_in=latest_check_in or window_records[0],
        )

    async def _get_or_create_user(self, user_id: UUID) -> User:
        user = await self._session.get(User, user_id)
        if user:
            return user

        user = User(id=user_id)
        self._session.add(user)
        await self._session.flush()
        return user

    def _coerce_uuid(self, value: str | UUID) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guardrail
            raise ValueError("Invalid user_id provided for mood check-in.") from exc

    def _validate_score(self, score: int) -> None:
        if score < 1 or score > 5:
            raise ValueError("Mood score must be between 1 and 5.")

    def _validate_energy(self, energy_level: int) -> None:
        if energy_level < 1 or energy_level > 5:
            raise ValueError("Energy level must be between 1 and 5.")

    def _normalize_tags(self, tags: Iterable[str] | None) -> list[str]:
        if not tags:
            return []
        cleaned = {tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()}
        return sorted(cleaned)

    def _normalize_text(self, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_timestamp(
        self,
        timestamp: datetime | None,
        tzinfo: ZoneInfo | timezone,
    ) -> datetime:
        if timestamp is None:
            localized = datetime.now(tzinfo)
        elif timestamp.tzinfo is None:
            localized = timestamp.replace(tzinfo=tzinfo)
        else:
            localized = timestamp.astimezone(tzinfo)
        return localized.astimezone(timezone.utc)

    def _resolve_timezone(self, user: User | None) -> ZoneInfo | timezone:
        if user and getattr(user, "timezone", None):
            try:
                return ZoneInfo(user.timezone)
            except ZoneInfoNotFoundError:  # pragma: no cover - depends on system tz database
                logger.debug("Unknown timezone %s; defaulting to UTC.", user.timezone)
        return timezone.utc

    def _aggregate_daily_scores(
        self,
        records: list[MoodCheckIn],
        tzinfo: ZoneInfo | timezone,
    ) -> dict[date, list[int]]:
        daily_scores: dict[date, list[int]] = defaultdict(list)
        for record in records:
            localized = record.check_in_at.astimezone(tzinfo)
            daily_scores[localized.date()].append(record.score)
        return daily_scores

    def _build_trend_points(
        self,
        daily_scores: dict[date, list[int]],
    ) -> list[MoodTrendPoint]:
        points: list[MoodTrendPoint] = []
        for day in sorted(daily_scores.keys()):
            scores = daily_scores[day]
            average = sum(scores) / len(scores)
            points.append(
                MoodTrendPoint(
                    date=day,
                    average_score=round(average, 2),
                    sample_count=len(scores),
                )
            )
        return points

    def _compute_streak(self, daily_scores: dict[date, list[int]]) -> int:
        if not daily_scores:
            return 0
        current_day = max(daily_scores.keys())
        streak = 0
        while current_day in daily_scores:
            day_scores = daily_scores[current_day]
            if any(score >= self._POSITIVE_THRESHOLD for score in day_scores):
                streak += 1
                current_day = current_day - timedelta(days=1)
            else:
                break
        return streak
