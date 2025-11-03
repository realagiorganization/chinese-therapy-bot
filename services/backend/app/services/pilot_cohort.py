from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotCohortParticipant
from app.schemas.pilot_cohort import (
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantListResponse,
    PilotParticipantResponse,
    PilotParticipantStatus,
    PilotParticipantUpdate,
)


logger = logging.getLogger(__name__)


class PilotCohortService:
    """Manage pilot cohort participant roster and engagement lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_participant(
        self,
        payload: PilotParticipantCreate,
    ) -> PilotCohortParticipant:
        record = PilotCohortParticipant(
            cohort=self._normalize_text(payload.cohort),
            participant_alias=self._normalize_optional(payload.participant_alias),
            contact_email=self._normalize_optional(payload.contact_email),
            contact_phone=self._normalize_optional(payload.contact_phone),
            channel=self._normalize_text(payload.channel or "web"),
            locale=self._normalize_text(payload.locale or "zh-CN"),
            status=payload.status.value,
            source=self._normalize_optional(payload.source),
            tags=self._normalize_tags(payload.tags),
            invite_sent_at=payload.invite_sent_at,
            onboarded_at=payload.onboarded_at,
            last_contacted_at=payload.last_contacted_at,
            consent_received=payload.consent_received,
            notes=self._normalize_optional(payload.notes),
            metadata_json=payload.metadata or {},
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_participants(
        self,
        filters: PilotParticipantFilters | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PilotParticipantListResponse:
        filters = filters or PilotParticipantFilters()
        base_stmt = select(PilotCohortParticipant)
        filtered_stmt = self._apply_filters(base_stmt, filters)
        total_stmt = self._apply_filters(
            select(func.count()),
            filters,
        )

        result = await self._session.execute(
            filtered_stmt.order_by(PilotCohortParticipant.created_at.asc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )
        participants = result.scalars().all()

        total_result = await self._session.execute(total_stmt)
        total = int(total_result.scalar_one())

        items = [self._to_response(participant) for participant in participants]
        return PilotParticipantListResponse(
            total=total,
            items=items,
        )

    async def get_participant(self, participant_id: UUID) -> PilotCohortParticipant | None:
        return await self._session.get(PilotCohortParticipant, participant_id)

    async def update_participant(
        self,
        participant_id: UUID,
        payload: PilotParticipantUpdate,
    ) -> PilotCohortParticipant:
        participant = await self.get_participant(participant_id)
        if not participant:
            raise ValueError("Participant not found.")

        if payload.cohort is not None:
            participant.cohort = self._normalize_text(payload.cohort)
        if payload.participant_alias is not None:
            participant.participant_alias = self._normalize_optional(payload.participant_alias)
        if payload.contact_email is not None:
            participant.contact_email = self._normalize_optional(payload.contact_email)
        if payload.contact_phone is not None:
            participant.contact_phone = self._normalize_optional(payload.contact_phone)
        if payload.channel is not None:
            participant.channel = self._normalize_text(payload.channel)
        if payload.locale is not None:
            participant.locale = self._normalize_text(payload.locale)
        if payload.status is not None:
            participant.status = payload.status.value
            if payload.status == PilotParticipantStatus.ACTIVE and not participant.onboarded_at:
                participant.onboarded_at = payload.onboarded_at or datetime.now(timezone.utc)
            if payload.status == PilotParticipantStatus.INVITED and not participant.invite_sent_at:
                participant.invite_sent_at = payload.invite_sent_at or datetime.now(timezone.utc)
        if payload.source is not None:
            participant.source = self._normalize_optional(payload.source)
        if payload.tags is not None:
            participant.tags = self._normalize_tags(payload.tags)
        if payload.invite_sent_at is not None:
            participant.invite_sent_at = payload.invite_sent_at
        if payload.onboarded_at is not None:
            participant.onboarded_at = payload.onboarded_at
        if payload.last_contacted_at is not None:
            participant.last_contacted_at = payload.last_contacted_at
        if payload.consent_received is not None:
            participant.consent_received = payload.consent_received
        if payload.notes is not None:
            participant.notes = self._normalize_optional(payload.notes)
        if payload.metadata is not None:
            participant.metadata_json = payload.metadata

        participant.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return participant

    def _apply_filters(
        self,
        stmt,
        filters: PilotParticipantFilters,
    ):
        if filters.cohort:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.cohort) == filters.cohort.lower()
            )
        if filters.status:
            stmt = stmt.where(PilotCohortParticipant.status == filters.status.value)
        if filters.channel:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.channel) == filters.channel.lower()
            )
        if filters.source:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.source) == filters.source.lower()
            )
        if filters.consent_received is not None:
            stmt = stmt.where(PilotCohortParticipant.consent_received == filters.consent_received)
        if filters.search:
            like_pattern = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PilotCohortParticipant.contact_email).like(like_pattern),
                    func.lower(PilotCohortParticipant.participant_alias).like(like_pattern),
                    func.lower(PilotCohortParticipant.contact_phone).like(like_pattern),
                )
            )
        return stmt

    def _normalize_tags(self, tags: Iterable[str] | None) -> list[str]:
        normalized: list[str] = []
        if not tags:
            return normalized
        seen: set[str] = set()
        for tag in tags:
            value = (tag or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        return normalized

    def _normalize_text(self, value: str) -> str:
        return value.strip()

    def _normalize_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def as_response(self, participant: PilotCohortParticipant) -> PilotParticipantResponse:
        """Public helper to serialize ORM instances for API responses."""
        return self._to_response(participant)

    def _to_response(self, participant: PilotCohortParticipant) -> PilotParticipantResponse:
        return PilotParticipantResponse(
            id=participant.id,
            cohort=participant.cohort,
            participant_alias=participant.participant_alias,
            contact_email=participant.contact_email,
            contact_phone=participant.contact_phone,
            channel=participant.channel,
            locale=participant.locale,
            status=PilotParticipantStatus(participant.status),
            source=participant.source,
            tags=list(participant.tags or []),
            invite_sent_at=participant.invite_sent_at,
            onboarded_at=participant.onboarded_at,
            last_contacted_at=participant.last_contacted_at,
            consent_received=participant.consent_received,
            notes=participant.notes,
            metadata=participant.metadata_json or {},
            created_at=participant.created_at,
            updated_at=participant.updated_at,
        )
