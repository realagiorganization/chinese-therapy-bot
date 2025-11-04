from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotCohortParticipant
from app.schemas.pilot_cohort import (
    FollowUpUrgency,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantStatus,
    PilotParticipantSummary,
    PilotParticipantSummaryBucket,
    PilotParticipantUpdate,
)
from app.services.pilot_cohort import PilotCohortService
from scripts.manage_pilot_cohort import render_summary_table


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


@pytest.mark.asyncio
async def test_plan_followups_returns_overdue_invite(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    sent_at = datetime.now(timezone.utc) - timedelta(days=4)
    participant = await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w9",
            participant_alias="Lily",
            status=PilotParticipantStatus.INVITED,
            invite_sent_at=sent_at,
        )
    )

    plan = await service.plan_followups(horizon_days=7)

    assert plan.total == 1
    followup = plan.items[0]
    assert followup.participant_id == participant.id
    assert followup.urgency in {FollowUpUrgency.DUE, FollowUpUrgency.OVERDUE}
    assert "Invitation was sent" in followup.reason
    assert "MindWell 体验邀约提醒" in followup.subject


@pytest.mark.asyncio
async def test_plan_followups_respects_filters_and_localization(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    last_contacted = datetime.now(timezone.utc) - timedelta(days=16)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w10",
            participant_alias="Ben",
            status=PilotParticipantStatus.ACTIVE,
            channel="mobile",
            locale="en-US",
            last_contacted_at=last_contacted,
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w10",
            participant_alias="Claire",
            status=PilotParticipantStatus.ACTIVE,
            channel="web",
            locale="zh-CN",
            last_contacted_at=last_contacted,
        )
    )

    filters = PilotParticipantFilters(channel="mobile")
    plan = await service.plan_followups(filters, horizon_days=21)

    assert plan.total == 1
    followup = plan.items[0]
    assert followup.channel == "mobile"
    assert followup.locale == "en-US"
    assert followup.subject == "MindWell wellness check-in"
    assert followup.urgency == FollowUpUrgency.OVERDUE


@pytest.mark.asyncio
async def test_summarize_participants_returns_metrics(cohort_session: AsyncSession) -> None:
    service = PilotCohortService(cohort_session)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w11",
            participant_alias="Amy",
            status=PilotParticipantStatus.ACTIVE,
            channel="mobile",
            locale="zh-CN",
            consent_received=True,
            tags=["sleep", "retreat"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w11",
            participant_alias="Brian",
            status=PilotParticipantStatus.ACTIVE,
            channel="web",
            locale="en-US",
            consent_received=False,
            tags=["sleep"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w12",
            participant_alias="Chloe",
            status=PilotParticipantStatus.INVITED,
            channel="wechat",
            locale="zh-CN",
            consent_received=True,
            tags=["stress"],
        )
    )

    summary = await service.summarize_participants()

    assert summary.total == 3
    assert summary.with_consent == 2
    assert summary.without_consent == 1

    status_counts = {bucket.key: bucket.total for bucket in summary.by_status}
    assert status_counts["active"] == 2
    assert status_counts["invited"] == 1

    channel_counts = {bucket.key: bucket.total for bucket in summary.by_channel}
    assert channel_counts["mobile"] == 1
    assert channel_counts["wechat"] == 1

    locale_counts = {bucket.key: bucket.total for bucket in summary.by_locale}
    assert locale_counts["zh-cn"] == 2
    assert locale_counts["en-us"] == 1

    top_tags = {bucket.key: bucket.total for bucket in summary.top_tags}
    assert top_tags["sleep"] == 2
    assert top_tags["stress"] == 1

    filtered = await service.summarize_participants(
        PilotParticipantFilters(cohort="pilot-2025w11")
    )
    assert filtered.total == 2
    assert filtered.by_status[0].key == "active"


def test_render_summary_table_formats_sections() -> None:
    summary = PilotParticipantSummary(
        total=4,
        with_consent=3,
        without_consent=1,
        by_status=[
            PilotParticipantSummaryBucket(key="active", total=2),
            PilotParticipantSummaryBucket(key="invited", total=2),
        ],
        by_channel=[
            PilotParticipantSummaryBucket(key="mobile", total=3),
            PilotParticipantSummaryBucket(key="web", total=1),
        ],
        by_locale=[
            PilotParticipantSummaryBucket(key="zh-cn", total=2),
            PilotParticipantSummaryBucket(key="en-us", total=2),
        ],
        top_tags=[
            PilotParticipantSummaryBucket(key="sleep", total=2),
            PilotParticipantSummaryBucket(key="stress", total=1),
        ],
    )

    table = render_summary_table(summary)

    assert "Total participants: 4" in table
    assert "Consent complete:   3 (75.0%)" in table
    assert "Status distribution" in table
    assert "active" in table
    assert "Top tags" in table
