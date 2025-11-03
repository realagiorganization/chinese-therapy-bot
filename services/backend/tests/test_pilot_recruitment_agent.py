from __future__ import annotations

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotParticipant
from app.schemas.feedback import PilotParticipantFilters
from app.services.feedback import PilotParticipantService
from app.agents.pilot_recruitment import PilotRecruitmentAgent


@pytest_asyncio.fixture()
async def participant_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PilotParticipant.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_import_candidates_creates_and_updates_records(participant_session: AsyncSession) -> None:
    service = PilotParticipantService(participant_session)
    agent = PilotRecruitmentAgent(service)

    records = [
        {
            "cohort": "pilot-2025w5",
            "full_name": "Naomi",
            "contact_email": "naomi@example.com",
            "status": "prospect",
            "channel": "web",
            "tags": ["priority"],
        },
        {
            "cohort": "pilot-2025w5",
            "full_name": "Naomi Zhang",
            "contact_email": "naomi@example.com",
            "status": "invited",
            "requires_follow_up": "false",
            "tags": "priority;voice",
        },
        {
            "cohort": "pilot-2025w5",
            "full_name": "Missing Contact",
        },
    ]

    result = await agent.import_candidates(
        records,
        cohort="pilot-2025w5",
        default_status="prospect",
        default_channel="web",
        tag_separator=";",
        dry_run=False,
    )

    assert result.total_rows == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.skipped == 1
    assert not result.dry_run

    summary = await service.summarize_participants(
        PilotParticipantFilters(cohort="pilot-2025w5")
    )
    assert summary.total == 1
    assert summary.status_breakdown["invited"] == 1
    assert summary.requires_follow_up == 0
    assert summary.tag_totals["priority"] == 1
    assert summary.tag_totals["voice"] == 1


@pytest.mark.asyncio
async def test_import_candidates_dry_run_reports_without_mutation(participant_session: AsyncSession) -> None:
    service = PilotParticipantService(participant_session)
    agent = PilotRecruitmentAgent(service)

    records = [
        {
            "cohort": "pilot-2025w5",
            "full_name": "Dry Run Candidate",
            "contact_email": "dryrun@example.com",
            "status": "prospect",
        }
    ]

    result = await agent.import_candidates(
        records,
        cohort="pilot-2025w5",
        default_status="prospect",
        default_channel="web",
        dry_run=True,
    )

    assert result.total_rows == 1
    assert result.created == 1
    assert result.updated == 0
    assert result.skipped == 0
    assert result.dry_run

    listing = await service.list_participants(PilotParticipantFilters(cohort="pilot-2025w5"))
    assert listing.total == 0
