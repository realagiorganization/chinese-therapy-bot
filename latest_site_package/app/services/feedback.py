from __future__ import annotations

from typing import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotFeedback
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
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
