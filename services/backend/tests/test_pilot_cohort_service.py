from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotCohortParticipant
from app.schemas.pilot_cohort import (
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantStatus,
    PilotParticipantUpdate,
)
from app.services.pilot_cohort import PilotCohortService


@pytest_asyncio.fixture()
async def cohort_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PilotCohortParticipant.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_participant_normalizes_fields(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    payload = PilotParticipantCreate(
        cohort=" pilot-2025w4 ",
        participant_alias=" Alice ",
        contact_email="alice@example.com ",
        contact_phone="  +86-13800000000 ",
        channel=" Mobile ",
        locale=" zh-CN ",
        status=PilotParticipantStatus.CONTACTED,
        source=" referral ",
        tags=[" Sleep ", "sleep", "  "],
        notes=" Prefers evening sessions ",
        consent_received=True,
    )

    participant = await service.create_participant(payload)

    assert participant.cohort == "pilot-2025w4"
    assert participant.participant_alias == "Alice"
    assert participant.contact_email == "alice@example.com"
    assert participant.contact_phone == "+86-13800000000"
    assert participant.channel == "Mobile"
    assert participant.locale == "zh-CN"
    assert participant.status == PilotParticipantStatus.CONTACTED.value
    assert participant.source == "referral"
    assert participant.tags == ["Sleep"]
    assert participant.notes == "Prefers evening sessions"
    assert participant.consent_received is True


@pytest.mark.asyncio
async def test_list_participants_applies_filters(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            participant_alias="Alice",
            contact_email="alice@example.com",
            status=PilotParticipantStatus.ACTIVE,
            tags=["sleep"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            participant_alias="Bob",
            contact_email="bob@example.com",
            status=PilotParticipantStatus.INVITED,
            consent_received=False,
            tags=["stress"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w5",
            participant_alias="Clara",
            contact_email="clara@example.com",
            status=PilotParticipantStatus.CONTACTED,
            source="wechat",
            tags=["sleep"],
        )
    )

    filtered = await service.list_participants(
        PilotParticipantFilters(
            cohort="pilot-2025w4",
            status=PilotParticipantStatus.ACTIVE,
            search="alice",
        )
    )

    assert filtered.total == 1
    assert len(filtered.items) == 1
    assert filtered.items[0].participant_alias == "Alice"
    assert filtered.items[0].status == PilotParticipantStatus.ACTIVE


@pytest.mark.asyncio
async def test_update_participant_adjusts_status_and_timestamps(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    participant = await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w6",
            participant_alias="Dana",
            contact_email="dana@example.com",
        )
    )

    updated = await service.update_participant(
        participant.id,
        PilotParticipantUpdate(
            status=PilotParticipantStatus.ACTIVE,
            tags=["journey"],
            consent_received=True,
        ),
    )

    assert updated.status == PilotParticipantStatus.ACTIVE.value
    assert updated.onboarded_at is not None
    assert updated.tags == ["journey"]
    assert updated.consent_received is True
