from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotFeedback
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
    PilotFeedbackReport,
    PilotFeedbackScorecard,
    PilotFeedbackTagStat,
    PilotFeedbackInsight,
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
        if filters.severity:
            conditions.append(PilotFeedback.severity == filters.severity)
        if filters.follow_up_needed is not None:
            conditions.append(PilotFeedback.follow_up_needed == filters.follow_up_needed)
        if filters.submitted_since:
            conditions.append(PilotFeedback.submitted_at >= filters.submitted_since)
        if filters.submitted_until:
            conditions.append(PilotFeedback.submitted_at <= filters.submitted_until)
        if filters.minimum_trust_score:
            conditions.append(PilotFeedback.trust_score >= filters.minimum_trust_score)

        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    async def summarize_feedback(
        self,
        filters: PilotFeedbackFilters | None = None,
        *,
        highlight_limit: int = 5,
    ) -> PilotFeedbackReport:
        """Aggregate pilot feedback metrics for stakeholder reports."""
        filters = filters or PilotFeedbackFilters()
        stmt = select(PilotFeedback).order_by(PilotFeedback.submitted_at.desc())
        stmt = self._apply_filters(stmt, filters)

        result = await self._session.execute(stmt)
        records = result.scalars().all()
        return self._build_report(records, filters, highlight_limit=highlight_limit)

    def _build_report(
        self,
        records: list[PilotFeedback],
        filters: PilotFeedbackFilters,
        *,
        highlight_limit: int,
    ) -> PilotFeedbackReport:
        generated_at = datetime.now(timezone.utc)
        total = len(records)
        if total == 0:
            return PilotFeedbackReport(
                generated_at=generated_at,
                total_entries=0,
                filters=filters,
                average_scores=PilotFeedbackScorecard(
                    average_sentiment=0.0,
                    average_trust=0.0,
                    average_usability=0.0,
                    tone_support_rate=0.0,
                    trust_confidence_rate=0.0,
                    usability_success_rate=0.0,
                ),
                severity_breakdown={},
                channel_breakdown={},
                role_breakdown={},
                tag_frequency=[],
                follow_up_required=0,
                recent_highlights=[],
                blocker_insights=[],
            )

        severity_counts = Counter((record.severity or "unspecified") for record in records)
        channel_counts = Counter(record.channel for record in records)
        role_counts = Counter(record.role for record in records)

        sentiments = [record.sentiment_score for record in records]
        trust_scores = [record.trust_score for record in records]
        usability_scores = [record.usability_score for record in records]

        def _avg(values: list[int]) -> float:
            return round(sum(values) / len(values), 2) if values else 0.0

        def _rate(values: list[int], threshold: int) -> float:
            if not values:
                return 0.0
            passed = sum(1 for value in values if value >= threshold)
            return round((passed / len(values)) * 100.0, 2)

        tags_counter: Counter[str] = Counter()
        for record in records:
            for tag in record.tags or []:
                normalized = tag.strip()
                if not normalized:
                    continue
                tags_counter[normalized] += 1

        tag_frequency = [
            PilotFeedbackTagStat(tag=name, count=count)
            for name, count in tags_counter.most_common(10)
        ]

        follow_up_required = sum(1 for record in records if record.follow_up_needed)

        def _to_insight(record: PilotFeedback) -> PilotFeedbackInsight:
            return PilotFeedbackInsight(
                cohort=record.cohort,
                role=record.role,
                channel=record.channel,
                scenario=record.scenario,
                participant_alias=record.participant_alias,
                sentiment_score=record.sentiment_score,
                trust_score=record.trust_score,
                usability_score=record.usability_score,
                severity=record.severity,
                tags=list(record.tags or []),
                highlights=record.highlights,
                blockers=record.blockers,
                follow_up_needed=record.follow_up_needed,
                submitted_at=record.submitted_at,
            )

        highlight_entries = [_to_insight(record) for record in records if record.highlights]
        blocker_entries = [
            _to_insight(record)
            for record in records
            if record.blockers
            or (record.severity or "").lower() in {"high", "critical", "blocker"}
        ]

        return PilotFeedbackReport(
            generated_at=generated_at,
            total_entries=total,
            filters=filters,
            average_scores=PilotFeedbackScorecard(
                average_sentiment=_avg(sentiments),
                average_trust=_avg(trust_scores),
                average_usability=_avg(usability_scores),
                tone_support_rate=_rate(sentiments, 4),
                trust_confidence_rate=_rate(trust_scores, 4),
                usability_success_rate=_rate(usability_scores, 4),
            ),
            severity_breakdown=dict(severity_counts),
            channel_breakdown=dict(channel_counts),
            role_breakdown=dict(role_counts),
            tag_frequency=tag_frequency,
            follow_up_required=follow_up_required,
            recent_highlights=highlight_entries[:highlight_limit],
            blocker_insights=blocker_entries[:highlight_limit],
        )

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
