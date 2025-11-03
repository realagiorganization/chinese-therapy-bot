from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotFeedback, PilotParticipant
from app.schemas.feedback import (
    PilotBacklogItem,
    PilotBacklogResponse,
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackItem,
    PilotFeedbackListResponse,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantItem,
    PilotParticipantListResponse,
    PilotParticipantUpdate,
    PilotParticipantSummary,
)


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


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PilotParticipantService:
    """Manage pilot participant recruitment and lifecycle state."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_participant(
        self, payload: PilotParticipantCreate
    ) -> PilotParticipantItem:
        channel = payload.channel.strip()
        if not channel:
            raise ValueError("Channel cannot be empty.")
        status = payload.status.strip()
        if not status:
            raise ValueError("Status cannot be empty.")

        cohort = payload.cohort.strip()
        if not cohort:
            raise ValueError("Cohort cannot be empty.")
        locale = (payload.locale or "zh-CN").strip()
        if not locale:
            raise ValueError("Locale cannot be empty.")

        participant = PilotParticipant(
            cohort=cohort,
            full_name=_strip_or_none(payload.full_name),
            preferred_name=_strip_or_none(payload.preferred_name),
            contact_email=_strip_or_none(payload.contact_email),
            contact_phone=_strip_or_none(payload.contact_phone),
            channel=channel,
            locale=locale,
            timezone=_strip_or_none(payload.timezone),
            organization=_strip_or_none(payload.organization),
            status=status,
            requires_follow_up=payload.requires_follow_up,
            invited_at=payload.invited_at,
            consent_signed_at=payload.consent_signed_at,
            onboarded_at=payload.onboarded_at,
            last_contact_at=payload.last_contact_at,
            follow_up_notes=_strip_or_none(payload.follow_up_notes),
            tags=_normalize_tags(payload.tags),
            metadata_json=payload.metadata or {},
        )
        self._session.add(participant)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                "A participant with this email is already tracked for the cohort."
            ) from exc

        await self._session.refresh(participant)
        return self._serialize(participant)

    async def _get_participant_by_cohort_email(
        self,
        cohort: str,
        contact_email: str | None,
    ) -> PilotParticipant | None:
        email = _strip_or_none(contact_email)
        if not email:
            return None
        stmt = select(PilotParticipant).where(
            PilotParticipant.cohort == cohort.strip(),
            func.lower(PilotParticipant.contact_email) == email.lower(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_participant_by_cohort_email(
        self,
        cohort: str,
        contact_email: str,
    ) -> PilotParticipantItem | None:
        record = await self._get_participant_by_cohort_email(cohort, contact_email)
        return self._serialize(record) if record else None

    async def upsert_participant(
        self,
        payload: PilotParticipantCreate,
    ) -> tuple[PilotParticipantItem, bool]:
        existing = (
            await self._get_participant_by_cohort_email(payload.cohort, payload.contact_email)
            if payload.contact_email
            else None
        )

        if existing:
            update_payload = PilotParticipantUpdate(
                full_name=payload.full_name,
                preferred_name=payload.preferred_name,
                contact_email=payload.contact_email,
                contact_phone=payload.contact_phone,
                channel=payload.channel,
                locale=payload.locale,
                timezone=payload.timezone,
                organization=payload.organization,
                status=payload.status,
                requires_follow_up=payload.requires_follow_up,
                invited_at=payload.invited_at,
                consent_signed_at=payload.consent_signed_at,
                onboarded_at=payload.onboarded_at,
                last_contact_at=payload.last_contact_at,
                follow_up_notes=payload.follow_up_notes,
                tags=list(payload.tags),
                metadata=payload.metadata,
            )
            updated = await self.update_participant(existing.id, update_payload)
            return updated, False

        created = await self.create_participant(payload)
        return created, True

    async def update_participant(
        self,
        participant_id: UUID,
        payload: PilotParticipantUpdate,
    ) -> PilotParticipantItem:
        participant = await self._session.get(PilotParticipant, participant_id)
        if not participant:
            raise ValueError("Pilot participant not found.")

        if payload.full_name is not None:
            participant.full_name = _strip_or_none(payload.full_name)
        if payload.preferred_name is not None:
            participant.preferred_name = _strip_or_none(payload.preferred_name)
        if payload.contact_email is not None:
            participant.contact_email = _strip_or_none(payload.contact_email)
        if payload.contact_phone is not None:
            participant.contact_phone = _strip_or_none(payload.contact_phone)
        if payload.channel is not None:
            channel = _strip_or_none(payload.channel)
            if not channel:
                raise ValueError("Channel cannot be empty.")
            participant.channel = channel
        if payload.locale is not None:
            locale = _strip_or_none(payload.locale)
            if not locale:
                raise ValueError("Locale cannot be empty.")
            participant.locale = locale
        if payload.timezone is not None:
            participant.timezone = _strip_or_none(payload.timezone)
        if payload.organization is not None:
            participant.organization = _strip_or_none(payload.organization)
        if payload.status is not None:
            status = _strip_or_none(payload.status)
            if not status:
                raise ValueError("Status cannot be empty.")
            participant.status = status
        if payload.requires_follow_up is not None:
            participant.requires_follow_up = payload.requires_follow_up
        if payload.invited_at is not None:
            participant.invited_at = payload.invited_at
        if payload.consent_signed_at is not None:
            participant.consent_signed_at = payload.consent_signed_at
        if payload.onboarded_at is not None:
            participant.onboarded_at = payload.onboarded_at
        if payload.last_contact_at is not None:
            participant.last_contact_at = payload.last_contact_at
        if payload.follow_up_notes is not None:
            participant.follow_up_notes = _strip_or_none(payload.follow_up_notes)
        if payload.tags is not None:
            participant.tags = _normalize_tags(payload.tags)
        if payload.metadata is not None:
            participant.metadata_json = payload.metadata

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                "A participant with this email is already tracked for the cohort."
            ) from exc

        await self._session.refresh(participant)
        return self._serialize(participant)

    async def list_participants(
        self,
        filters: PilotParticipantFilters | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PilotParticipantListResponse:
        filters = filters or PilotParticipantFilters()
        stmt = select(PilotParticipant).order_by(
            PilotParticipant.requires_follow_up.desc(),
            PilotParticipant.created_at.desc(),
        )
        stmt = self._apply_filters(stmt, filters)

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        if filters.tag:
            tag_lower = filters.tag.strip().lower()
            records = [
                record
                for record in records
                if any(tag_lower == str(tag).strip().lower() for tag in record.tags or [])
            ]

        total = len(records)
        paginated = records[offset : offset + limit]

        return PilotParticipantListResponse(
            total=total,
            items=[self._serialize(record) for record in paginated],
        )

    async def summarize_participants(
        self,
        filters: PilotParticipantFilters | None = None,
    ) -> PilotParticipantSummary:
        filters = filters or PilotParticipantFilters()
        stmt = select(PilotParticipant)
        stmt = self._apply_filters(stmt, filters)
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        status_counts: Counter[str] = Counter()
        tag_counts: Counter[str] = Counter()
        requires_follow_up = 0
        invited = 0
        consented = 0
        onboarded = 0
        contactable = 0
        pending_invites = 0
        last_activity: datetime | None = None

        for record in records:
            status_counts[record.status] += 1
            for tag in record.tags or []:
                normalized = str(tag).strip()
                if normalized:
                    tag_counts[normalized] += 1

            if record.requires_follow_up:
                requires_follow_up += 1
            if record.contact_email or record.contact_phone:
                contactable += 1
            if record.invited_at:
                invited += 1
            if record.consent_signed_at:
                consented += 1
            if record.onboarded_at:
                onboarded += 1
            if record.status.lower() in {"prospect", "invited"} and not record.onboarded_at:
                pending_invites += 1

            for candidate in (
                record.last_contact_at,
                record.updated_at,
                record.invited_at,
                record.consent_signed_at,
                record.onboarded_at,
            ):
                candidate_utc = _ensure_utc(candidate)
                if not candidate_utc:
                    continue
                if not last_activity or candidate_utc > last_activity:
                    last_activity = candidate_utc

        summary = PilotParticipantSummary(
            cohort=filters.cohort,
            total=len(records),
            status_breakdown=dict(sorted(status_counts.items(), key=lambda item: item[0])),
            requires_follow_up=requires_follow_up,
            with_contact_methods=contactable,
            invited=invited,
            consented=consented,
            onboarded=onboarded,
            pending_invites=pending_invites,
            last_activity_at=last_activity,
            tag_totals=dict(sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))),
        )
        return summary

    def _apply_filters(
        self,
        stmt: Select,
        filters: PilotParticipantFilters,
    ) -> Select:
        conditions: list = []
        if filters.cohort:
            conditions.append(PilotParticipant.cohort == filters.cohort)
        if filters.status:
            conditions.append(PilotParticipant.status == filters.status)
        if filters.requires_follow_up is not None:
            conditions.append(
                PilotParticipant.requires_follow_up == filters.requires_follow_up
            )
        if conditions:
            stmt = stmt.where(*conditions)

        return stmt

    @staticmethod
    def _serialize(record: PilotParticipant) -> PilotParticipantItem:
        return PilotParticipantItem(
            id=record.id,
            cohort=record.cohort,
            full_name=record.full_name,
            preferred_name=record.preferred_name,
            contact_email=record.contact_email,
            contact_phone=record.contact_phone,
            channel=record.channel,
            locale=record.locale,
            timezone=record.timezone,
            organization=record.organization,
            status=record.status,
            requires_follow_up=record.requires_follow_up,
            invited_at=record.invited_at,
            consent_signed_at=record.consent_signed_at,
            onboarded_at=record.onboarded_at,
            last_contact_at=record.last_contact_at,
            follow_up_notes=record.follow_up_notes,
            tags=list(record.tags or []),
            metadata=record.metadata_json or {},
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class PilotFeedbackService:
    """Capture and query structured pilot feedback for UAT tracking."""

    def __init__(self, session: AsyncSession):
        self._session = session

    @dataclass
    class _BacklogAggregate:
        label: str
        is_tag: bool
        cohorts: Counter = field(default_factory=Counter)
        scenarios: Counter = field(default_factory=Counter)
        severity_counts: Counter = field(default_factory=Counter)
        frequency: int = 0
        follow_up_count: int = 0
        sentiment_total: float = 0.0
        trust_total: float = 0.0
        usability_total: float = 0.0
        participant_ids: set[UUID | None] = field(default_factory=set)
        highlights: list[str] = field(default_factory=list)
        blockers: list[str] = field(default_factory=list)
        last_submitted_at: datetime | None = None

        def ingest(self, record: PilotFeedback) -> None:
            self.frequency += 1
            self.cohorts.update([record.cohort])
            if record.scenario:
                self.scenarios.update([record.scenario])
            severity = (record.severity or "").strip().lower() or "unspecified"
            self.severity_counts.update([severity])
            if record.follow_up_needed:
                self.follow_up_count += 1
            self.sentiment_total += float(record.sentiment_score)
            self.trust_total += float(record.trust_score)
            self.usability_total += float(record.usability_score)
            if record.participant_id:
                self.participant_ids.add(record.participant_id)
            if record.highlights:
                if record.highlights not in self.highlights:
                    self.highlights.append(record.highlights)
            if record.blockers:
                if record.blockers not in self.blockers:
                    self.blockers.append(record.blockers)
            if not self.last_submitted_at or record.submitted_at > self.last_submitted_at:
                self.last_submitted_at = record.submitted_at

        def to_schema(self) -> PilotBacklogItem:
            severity_weights = {
                "critical": 5,
                "high": 4,
                "major": 4,
                "medium": 3,
                "moderate": 3,
                "low": 2,
                "minor": 2,
                "unspecified": 1,
            }
            representative_severity = None
            highest_weight = -1
            for severity, count in self.severity_counts.items():
                weight = severity_weights.get(severity, 1)
                if weight > highest_weight or (
                    weight == highest_weight
                    and self.severity_counts[severity]
                    > self.severity_counts.get(representative_severity or "", 0)
                ):
                    representative_severity = severity
                    highest_weight = weight

            avg_sentiment = self.sentiment_total / self.frequency if self.frequency else 0.0
            avg_trust = self.trust_total / self.frequency if self.frequency else 0.0
            avg_usability = self.usability_total / self.frequency if self.frequency else 0.0

            def _gap(value: float) -> float:
                return max(0.0, 4.0 - value)

            priority_score = (
                highest_weight * 2.0
                + self.frequency * 0.75
                + self.follow_up_count * 1.5
                + _gap(avg_sentiment)
                + (_gap(avg_trust) * 1.2)
                + (_gap(avg_usability) * 0.8)
            )

            most_common_scenario = None
            if self.scenarios:
                most_common_scenario = self.scenarios.most_common(1)[0][0]

            cohorts = sorted({cohort for cohort, _count in self.cohorts.items()})
            highlights = self.highlights[:3]
            blockers = self.blockers[:3]
            return PilotBacklogItem(
                label=self.label,
                cohorts=cohorts,
                tag=self.label if self.is_tag else None,
                scenario=most_common_scenario,
                representative_severity=representative_severity,
                frequency=self.frequency,
                participant_count=len({pid for pid in self.participant_ids if pid}),
                follow_up_count=self.follow_up_count,
                average_sentiment=round(avg_sentiment, 2),
                average_trust=round(avg_trust, 2),
                average_usability=round(avg_usability, 2),
                priority_score=round(priority_score, 2),
                last_submitted_at=self.last_submitted_at or datetime.utcnow(),
                highlights=highlights,
                blockers=blockers,
            )

    async def record_feedback(self, payload: PilotFeedbackCreate) -> PilotFeedbackItem:
        """Persist a pilot feedback entry and return the serialized record."""
        normalized_tags = _normalize_tags(payload.tags)
        participant_id = payload.participant_id
        if participant_id:
            participant = await self._session.get(PilotParticipant, participant_id)
            if not participant:
                raise ValueError("Pilot participant not found.")
        entry = PilotFeedback(
            user_id=payload.user_id,
            cohort=payload.cohort.strip(),
            participant_alias=self._strip_or_none(payload.participant_alias),
            contact_email=self._strip_or_none(payload.contact_email),
            participant_id=participant_id,
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

    async def generate_backlog(
        self,
        filters: PilotFeedbackFilters | None = None,
        *,
        limit: int = 20,
    ) -> PilotBacklogResponse:
        """Aggregate pilot feedback into a prioritized backlog view."""
        filters = filters or PilotFeedbackFilters()
        stmt = select(PilotFeedback).order_by(PilotFeedback.submitted_at.desc())
        stmt = self._apply_filters(stmt, filters)

        result = await self._session.execute(stmt)
        records = result.scalars().all()
        if not records:
            return PilotBacklogResponse(total=0, items=[])

        aggregates: dict[str, PilotFeedbackService._BacklogAggregate] = {}

        for record in records:
            tag_labels = [tag for tag in record.tags or [] if tag and tag.strip()]
            fallback_label = (record.scenario or "general").strip() or "general"

            groups = tag_labels if tag_labels else [fallback_label]
            is_tag_source = bool(tag_labels)

            for raw_label in groups:
                label = raw_label.strip() or fallback_label
                normalized = label.lower()
                aggregate = aggregates.get(normalized)
                if aggregate is None:
                    aggregate = self._BacklogAggregate(
                        label=label,
                        is_tag=is_tag_source,
                    )
                    aggregates[normalized] = aggregate
                else:
                    aggregate.is_tag = aggregate.is_tag or is_tag_source
                    if not aggregate.label.strip():
                        aggregate.label = label
                aggregate.ingest(record)

        backlog_items = [aggregate.to_schema() for aggregate in aggregates.values()]
        backlog_items.sort(
            key=lambda item: (item.priority_score, item.last_submitted_at),
            reverse=True,
        )

        sliced = backlog_items[:limit] if limit else backlog_items
        return PilotBacklogResponse(total=len(backlog_items), items=sliced)

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
    def _serialize(record: PilotFeedback) -> PilotFeedbackItem:
        return PilotFeedbackItem(
            id=record.id,
            cohort=record.cohort,
            role=record.role,
            channel=record.channel,
            scenario=record.scenario,
            participant_alias=record.participant_alias,
            contact_email=record.contact_email,
            participant_id=record.participant_id,
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

    @staticmethod
    def _strip_or_none(value: str | None) -> str | None:
        return _strip_or_none(value)
