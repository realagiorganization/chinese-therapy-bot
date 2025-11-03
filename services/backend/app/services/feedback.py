from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotFeedback
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
    PilotFeedbackSummary,
    PilotFeedbackGroupSummary,
    PilotFeedbackTagSummary,
)


class PilotFeedbackService:
    """Capture and query structured pilot feedback for UAT tracking."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def record_feedback(self, payload: PilotFeedbackCreate) -> PilotFeedbackItem:
        """Persist a pilot feedback entry and return the serialized record."""
        normalized_tags = self._normalize_tags(payload.tags)
        entry = PilotFeedback(
            user_id=payload.user_id,
            cohort=payload.cohort.strip(),
            participant_alias=self._strip_or_none(payload.participant_alias),
            contact_email=self._strip_or_none(payload.contact_email),
            role=payload.role.strip(),
            channel=payload.channel.strip(),
            scenario=self._strip_or_none(payload.scenario),
            sentiment_score=payload.sentiment_score,
            trust_score=payload.trust_score,
            usability_score=payload.usability_score,
            severity=self._strip_or_none(payload.severity),
            tags=normalized_tags,
            highlights=self._strip_or_none(payload.highlights),
            blockers=self._strip_or_none(payload.blockers),
            follow_up_needed=payload.follow_up_needed,
            metadata_json=payload.metadata or None,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return self._serialize(entry)

    async def list_feedback(
        self,
        filters: PilotFeedbackFilters | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PilotFeedbackListResponse:
        """Return filtered feedback entries ordered by recency."""
        filters = filters or PilotFeedbackFilters()
        stmt = select(PilotFeedback).order_by(PilotFeedback.submitted_at.desc())
        stmt = self._apply_filters(stmt, filters)
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        count_stmt = select(func.count(PilotFeedback.id))
        count_stmt = self._apply_filters(count_stmt, filters)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        return PilotFeedbackListResponse(
            total=int(total or 0),
            items=[self._serialize(record) for record in records],
        )

    async def summarize_feedback(
        self,
        filters: PilotFeedbackFilters | None = None,
        *,
        top_tag_limit: int = 10,
    ) -> PilotFeedbackSummary:
        """Return aggregated scoring insights for pilot feedback entries."""
        filters = filters or PilotFeedbackFilters()
        stmt = select(PilotFeedback)
        stmt = self._apply_filters(stmt, filters)
        result = await self._session.execute(stmt)
        entries = list(result.scalars().all())

        total_entries = len(entries)

        def _avg(values: Iterable[int]) -> float | None:
            values = list(values)
            if not values:
                return None
            return round(sum(values) / len(values), 2)

        average_sentiment = _avg(entry.sentiment_score for entry in entries)
        average_trust = _avg(entry.trust_score for entry in entries)
        average_usability = _avg(entry.usability_score for entry in entries)
        follow_up_needed = sum(1 for entry in entries if entry.follow_up_needed)

        tag_counts: Counter[str] = Counter()
        for entry in entries:
            for tag in entry.tags or []:
                if not tag:
                    continue
                tag_counts[tag] += 1

        top_tags = [
            PilotFeedbackTagSummary(tag=tag, count=count)
            for tag, count in tag_counts.most_common(top_tag_limit)
        ]

        def _summaries_by(field: str) -> list[PilotFeedbackGroupSummary]:
            buckets: dict[str, list[PilotFeedback]] = defaultdict(list)
            for entry in entries:
                raw_key = getattr(entry, field, None)
                key = str(raw_key).strip() if raw_key else "unspecified"
                buckets[key].append(entry)

            summaries: list[PilotFeedbackGroupSummary] = []
            for key, bucket in buckets.items():
                summaries.append(
                    PilotFeedbackGroupSummary(
                        key=key,
                        total=len(bucket),
                        average_sentiment=_avg(item.sentiment_score for item in bucket),
                        average_trust=_avg(item.trust_score for item in bucket),
                        average_usability=_avg(item.usability_score for item in bucket),
                        follow_up_needed=sum(1 for item in bucket if item.follow_up_needed),
                    )
                )

            summaries.sort(key=lambda item: (-item.total, item.key.lower()))
            return summaries

        return PilotFeedbackSummary(
            total_entries=total_entries,
            average_sentiment=average_sentiment,
            average_trust=average_trust,
            average_usability=average_usability,
            follow_up_needed=follow_up_needed,
            top_tags=top_tags,
            by_cohort=_summaries_by("cohort"),
            by_channel=_summaries_by("channel"),
            by_role=_summaries_by("role"),
        )

    def _apply_filters(
        self,
        stmt: Select,
        filters: PilotFeedbackFilters,
    ) -> Select:
        conditions: list = []
        if filters.cohort:
            conditions.append(PilotFeedback.cohort == filters.cohort)
        if filters.channel:
            conditions.append(PilotFeedback.channel == filters.channel)
        if filters.role:
            conditions.append(PilotFeedback.role == filters.role)
        if filters.minimum_trust_score:
            conditions.append(PilotFeedback.trust_score >= filters.minimum_trust_score)

        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    @staticmethod
    def _normalize_tags(tags: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags or []:
            stripped = str(tag).strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(stripped)
        return normalized

    @staticmethod
    def _strip_or_none(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _serialize(record: PilotFeedback) -> PilotFeedbackItem:
        return PilotFeedbackItem(
            id=record.id,
            cohort=record.cohort,
            role=record.role,
            channel=record.channel,
            scenario=record.scenario,
            participant_alias=record.participant_alias,
            contact_email=record.contact_email,
            sentiment_score=record.sentiment_score,
            trust_score=record.trust_score,
            usability_score=record.usability_score,
            severity=record.severity,
            tags=list(record.tags or []),
            highlights=record.highlights,
            blockers=record.blockers,
            follow_up_needed=record.follow_up_needed,
            metadata=record.metadata_json or {},
            submitted_at=record.submitted_at,
        )
