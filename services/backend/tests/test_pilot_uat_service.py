from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotCohortParticipant, PilotUATSession
from app.schemas.pilot_cohort import PilotParticipantCreate, PilotParticipantStatus
from app.schemas.pilot_uat import (
    PilotUATIssue,
    PilotUATSessionCreate,
    PilotUATSessionFilters,
)
from app.services.pilot_cohort import PilotCohortService
from app.services.pilot_uat import PilotUATService


@pytest_asyncio.fixture()
async def uat_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PilotCohortParticipant.__table__.create)
        await conn.run_sync(PilotUATSession.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_log_session_normalizes_payload(uat_session: AsyncSession) -> None:
    cohort_service = PilotCohortService(uat_session)
    participant = await cohort_service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            participant_alias="Alice",
            status=PilotParticipantStatus.ACTIVE,
        )
    )
    service = PilotUATService(uat_session)

    payload = PilotUATSessionCreate(
        participant_id=participant.id,
        cohort=" pilot-2025w4 ",
        participant_alias=" Alice ",
        facilitator=" Product  ",
        scenario=" Journey ",
        environment=" QA ",
        platform=" Mobile ",
        device=" iPhone 12 ",
        satisfaction_score=5,
        trust_score=4,
        highlights=" Loved the spotlight summaries. ",
        blockers=" Voice input stalled once. ",
        notes=" Needs better onboarding copy. ",
        issues=[
            PilotUATIssue(title="Latency spike ", severity=" High ", notes="Occurred during summary refresh."),
            PilotUATIssue(title="Copy issue", severity=None, notes=None),
        ],
        action_items=[" tighten prompts ", "Tighten prompts"],
    )

    record = await service.log_session(payload)

    assert record.cohort == "pilot-2025w4"
    assert record.participant_alias == "Alice"
    assert record.participant_id == participant.id
    assert record.facilitator == "Product"
    assert record.environment == "QA"
    assert record.platform == "Mobile"
    assert len(record.issues) == 2
    assert record.issues[0].severity == "high"
    assert record.action_items == ["tighten prompts"]
    assert record.metadata == {}


@pytest.mark.asyncio
async def test_list_sessions_applies_filters(uat_session: AsyncSession) -> None:
    service = PilotUATService(uat_session)
    now = datetime.now(timezone.utc)

    first = await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w7",
            participant_alias="Ming",
            session_date=now - timedelta(days=1),
            environment="qa",
            platform="web",
            satisfaction_score=4,
        )
    )
    await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w7",
            participant_alias="Liu",
            session_date=now,
            environment="pilot",
            platform="mobile",
            satisfaction_score=2,
        )
    )

    filters = PilotUATSessionFilters(
        cohort="pilot-2025w7",
        platform="web",
        occurred_before=now,
    )
    response = await service.list_sessions(filters, limit=10, offset=0)

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].participant_alias == first.participant_alias


@pytest.mark.asyncio
async def test_summarize_sessions_returns_aggregated_metrics(uat_session: AsyncSession) -> None:
    service = PilotUATService(uat_session)
    await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w8",
            participant_alias="Kai",
            platform="web",
            environment="qa",
            satisfaction_score=5,
            trust_score=4,
            issues=[
                PilotUATIssue(title="Latency", severity="High"),
                PilotUATIssue(title="Copy", severity="Medium"),
            ],
        )
    )
    await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w8",
            participant_alias="Zhao",
            platform="mobile",
            environment="qa",
            satisfaction_score=3,
            trust_score=2,
            blockers="Audio muted unexpectedly.",
            issues=[PilotUATIssue(title="Audio bug", severity="High")],
        )
    )

    summary = await service.summarize_sessions(
        PilotUATSessionFilters(cohort="pilot-2025w8")
    )

    assert summary.total_sessions == 2
    assert summary.distinct_participants == 2
    assert summary.average_satisfaction == 4.0
    assert summary.average_trust == 3.0
    assert summary.sessions_with_blockers == 1
    assert summary.issues_by_severity[0].severity == "high"
    assert summary.issues_by_severity[0].count == 2
    assert summary.sessions_by_platform[0].key in {"web", "mobile"}


@pytest.mark.asyncio
async def test_prioritize_backlog_groups_recurrent_issues(uat_session: AsyncSession) -> None:
    service = PilotUATService(uat_session)
    await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w9",
            participant_alias="Chen",
            platform="web",
            action_items=["Review caching"],
            issues=[
                PilotUATIssue(title="Latency spike", severity="High", notes="Home timeline stalled."),
                PilotUATIssue(title="Copy tweak", severity="Low", notes="CTA needs localization."),
            ],
        )
    )
    await service.log_session(
        PilotUATSessionCreate(
            cohort="pilot-2025w9",
            participant_alias="Ling",
            platform="mobile",
            action_items=["Review caching", "Profile loading audit"],
            issues=[
                PilotUATIssue(title="Latency spike", severity="Medium", notes="Summary refresh slow."),
            ],
        )
    )

    backlog = await service.prioritize_backlog(
        PilotUATSessionFilters(cohort="pilot-2025w9"),
        limit=5,
    )

    assert backlog.total == 2
    assert backlog.items[0].title.lower().startswith("latency")
    assert backlog.items[0].severity == "high"
    assert backlog.items[0].occurrences == 2
    assert backlog.items[0].affected_participants == 2
    assert "Review caching" in backlog.items[0].action_items
    assert backlog.items[1].title.lower().startswith("copy")
