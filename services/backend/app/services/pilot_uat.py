from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import PilotUATSession
from app.schemas.pilot_uat import (
    PilotUATIssue,
    PilotUATGroupSummary,
    PilotUATIssueSummary,
    PilotUATSessionCreate,
    PilotUATSessionFilters,
    PilotUATSessionListResponse,
    PilotUATSessionResponse,
    PilotUATSessionSummary,
)


class PilotUATService:
    """Manage pilot UAT session logs and aggregated insights."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_session(self, payload: PilotUATSessionCreate) -> PilotUATSessionResponse:
        """Persist a UAT session entry and return the serialized record."""
        issues = [self._normalize_issue(issue) for issue in payload.issues or []]
        action_items = self._normalize_action_items(payload.action_items or [])
        record = PilotUATSession(
            participant_id=payload.participant_id,
            cohort=payload.cohort.strip(),
            participant_alias=self._strip_or_none(payload.participant_alias),
            session_date=self._normalize_datetime(payload.session_date),
            facilitator=self._strip_or_none(payload.facilitator),
            scenario=self._strip_or_none(payload.scenario),
            environment=self._strip_or_none(payload.environment),
            platform=self._strip_or_none(payload.platform),
            device=self._strip_or_none(payload.device),
            satisfaction_score=payload.satisfaction_score,
            trust_score=payload.trust_score,
            highlights=self._strip_or_none(payload.highlights),
            blockers=self._strip_or_none(payload.blockers),
            notes=self._strip_or_none(payload.notes),
            issues=issues,
            action_items=action_items,
            metadata_json=payload.metadata or {},
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return self._serialize(record)

    async def list_sessions(
        self,
        filters: PilotUATSessionFilters | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PilotUATSessionListResponse:
        """Return paginated session entries filtered by metadata."""
        filters = filters or PilotUATSessionFilters()
        stmt = select(PilotUATSession).order_by(PilotUATSession.session_date.desc())
        stmt = self._apply_filters(stmt, filters)
        stmt = stmt.limit(max(limit, 1)).offset(max(offset, 0))

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        count_stmt = select(func.count(PilotUATSession.id))
        count_stmt = self._apply_filters(count_stmt, filters)
        total = await self._session.scalar(count_stmt)

        return PilotUATSessionListResponse(
            total=int(total or 0),
            items=[self._serialize(record) for record in records],
        )

    async def summarize_sessions(
        self,
        filters: PilotUATSessionFilters | None = None,
    ) -> PilotUATSessionSummary:
        """Return aggregated metrics across recorded sessions."""
        filters = filters or PilotUATSessionFilters()
        stmt = select(PilotUATSession)
        stmt = self._apply_filters(stmt, filters)
        result = await self._session.execute(stmt)
        records: list[PilotUATSession] = list(result.scalars().all())

        total_sessions = len(records)
        if total_sessions == 0:
            return PilotUATSessionSummary(
                total_sessions=0,
                distinct_participants=0,
                average_satisfaction=None,
                average_trust=None,
                sessions_with_blockers=0,
                issues_by_severity=[],
                sessions_by_platform=[],
                sessions_by_environment=[],
            )

        def _average(values: Iterable[int | None]) -> float | None:
            filtered = [value for value in values if value is not None]
            if not filtered:
                return None
            return round(sum(filtered) / len(filtered), 2)

        distinct_participant_keys: set[str] = set()
        sessions_with_blockers = 0
        severity_counts: Counter[str] = Counter()
        platform_buckets: dict[str, list[PilotUATSession]] = defaultdict(list)
        environment_buckets: dict[str, list[PilotUATSession]] = defaultdict(list)

        for record in records:
            key = self._participant_key(record)
            if key:
                distinct_participant_keys.add(key)
            if record.blockers:
                sessions_with_blockers += 1

            platform = (record.platform or "unspecified").lower()
            environment = (record.environment or "unspecified").lower()
            platform_buckets[platform].append(record)
            environment_buckets[environment].append(record)

            for issue in record.issues or []:
                severity = str(issue.get("severity") or "unspecified").lower()
                severity_counts[severity] += 1

        issues_by_severity = [
            PilotUATIssueSummary(severity=severity, count=count)
            for severity, count in severity_counts.most_common()
        ]

        def _summaries(buckets: dict[str, list[PilotUATSession]]) -> list[PilotUATGroupSummary]:
            summaries: list[PilotUATGroupSummary] = []
            for key, bucket in buckets.items():
                summaries.append(
                    PilotUATGroupSummary(
                        key=key,
                        total=len(bucket),
                        average_satisfaction=_average(
                            session.satisfaction_score for session in bucket
                        ),
                        average_trust=_average(session.trust_score for session in bucket),
                    )
                )
            summaries.sort(key=lambda item: (-item.total, item.key))
            return summaries

        return PilotUATSessionSummary(
            total_sessions=total_sessions,
            distinct_participants=len(distinct_participant_keys),
            average_satisfaction=_average(record.satisfaction_score for record in records),
            average_trust=_average(record.trust_score for record in records),
            sessions_with_blockers=sessions_with_blockers,
            issues_by_severity=issues_by_severity,
            sessions_by_platform=_summaries(platform_buckets),
            sessions_by_environment=_summaries(environment_buckets),
        )

    def _apply_filters(
        self,
        stmt: Select,
        filters: PilotUATSessionFilters,
    ) -> Select:
        conditions: list[Any] = []
        if filters.cohort:
            conditions.append(PilotUATSession.cohort == filters.cohort)
        if filters.participant_id:
            conditions.append(PilotUATSession.participant_id == filters.participant_id)
        if filters.participant_alias:
            conditions.append(
                func.lower(PilotUATSession.participant_alias) == filters.participant_alias.lower()
            )
        if filters.platform:
            conditions.append(
                func.lower(PilotUATSession.platform) == filters.platform.lower()
            )
        if filters.environment:
            conditions.append(
                func.lower(PilotUATSession.environment) == filters.environment.lower()
            )
        if filters.facilitator:
            conditions.append(
                func.lower(PilotUATSession.facilitator) == filters.facilitator.lower()
            )
        if filters.scenario:
            conditions.append(
                func.lower(PilotUATSession.scenario) == filters.scenario.lower()
            )
        if filters.occurred_after:
            conditions.append(PilotUATSession.session_date >= filters.occurred_after)
        if filters.occurred_before:
            conditions.append(PilotUATSession.session_date <= filters.occurred_before)

        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_issue(issue: PilotUATIssue) -> dict[str, Any]:
        title = issue.title.strip()
        severity = issue.severity.strip() if issue.severity else None
        notes = issue.notes.strip() if issue.notes else None
        payload: dict[str, Any] = {"title": title}
        if severity:
            payload["severity"] = severity.lower()
        if notes:
            payload["notes"] = notes
        return payload

    @staticmethod
    def _normalize_action_items(items: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            stripped = str(item).strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(stripped)
        return normalized

    @staticmethod
    def _participant_key(record: PilotUATSession) -> str | None:
        if record.participant_id:
            return str(record.participant_id)
        if record.participant_alias:
            return record.participant_alias.lower()
        return None

    @staticmethod
    def _strip_or_none(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _serialize(record: PilotUATSession) -> PilotUATSessionResponse:
        metadata = record.metadata_json or {}
        issues = [
            PilotUATIssue(
                title=issue.get("title", ""),
                severity=issue.get("severity"),
                notes=issue.get("notes"),
            )
            for issue in (record.issues or [])
        ]
        return PilotUATSessionResponse(
            id=record.id,
            cohort=record.cohort,
            participant_alias=record.participant_alias,
            participant_id=record.participant_id,
            session_date=record.session_date,
            facilitator=record.facilitator,
            scenario=record.scenario,
            environment=record.environment,
            platform=record.platform,
            device=record.device,
            satisfaction_score=record.satisfaction_score,
            trust_score=record.trust_score,
            highlights=record.highlights,
            blockers=record.blockers,
            notes=record.notes,
            issues=issues,
            action_items=record.action_items or [],
            metadata=metadata,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
