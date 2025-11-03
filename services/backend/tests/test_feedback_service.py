from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotFeedback, PilotParticipant, User
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantUpdate,
)
from app.services.feedback import PilotFeedbackService, PilotParticipantService


@pytest_asyncio.fixture()
async def feedback_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(PilotParticipant.__table__.create)
        await conn.run_sync(PilotFeedback.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_record_feedback_normalizes_tags(feedback_session: AsyncSession) -> None:
    service = PilotFeedbackService(feedback_session)
    payload = PilotFeedbackCreate(
        cohort="pilot-2025w4",
        channel="mobile ",
        role="Participant ",
        scenario=" chat-flow ",
        sentiment_score=4,
        trust_score=5,
        usability_score=3,
        tags=["Navigation", "navigation", "  Copywriting  ", ""],
        highlights="Enjoyed the therapist suggestions",
        blockers="Streaming stalled once.",
        follow_up_needed=True,
        metadata={"device": "iPhone 12"},
    )

    entry = await service.record_feedback(payload)

    assert entry.id is not None
    assert entry.channel == "mobile"
    assert entry.role == "Participant"
    assert entry.scenario == "chat-flow"
    assert entry.tags == ["Navigation", "Copywriting"]
    assert entry.follow_up_needed is True
    assert entry.metadata == {"device": "iPhone 12"}


@pytest.mark.asyncio
async def test_list_feedback_filters_results(feedback_session: AsyncSession) -> None:
    service = PilotFeedbackService(feedback_session)
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            channel="web",
            role="participant",
            sentiment_score=5,
            trust_score=5,
            usability_score=4,
            tags=["delight"],
        )
    )
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            channel="mobile",
            role="participant",
            sentiment_score=3,
            trust_score=2,
            usability_score=3,
            tags=["latency"],
        )
    )
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w5",
            channel="web",
            role="therapist",
            sentiment_score=4,
            trust_score=4,
            usability_score=4,
            tags=["directory"],
        )
    )

    filtered = await service.list_feedback(
        PilotFeedbackFilters(cohort="pilot-2025w4", minimum_trust_score=3)
    )

    assert filtered.total == 1
    assert len(filtered.items) == 1
    assert filtered.items[0].tags == ["delight"]


@pytest.mark.asyncio
async def test_record_feedback_links_participant(feedback_session: AsyncSession) -> None:
    participant_service = PilotParticipantService(feedback_session)
    participant = await participant_service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Test User",
            contact_email="test@example.com",
            status="invited",
        )
    )

    feedback_service = PilotFeedbackService(feedback_session)
    entry = await feedback_service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            participant_id=participant.id,
            channel="web",
            role="participant",
            sentiment_score=4,
            trust_score=4,
            usability_score=4,
            tags=["coaching"],
        )
    )

    assert entry.participant_id == participant.id


@pytest.mark.asyncio
async def test_create_participant_and_filter_by_tag(feedback_session: AsyncSession) -> None:
    service = PilotParticipantService(feedback_session)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Alice",
            contact_email="alice@example.com",
            tags=["priority", "early"],
            requires_follow_up=True,
            status="enrolled",
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Bob",
            contact_email="bob@example.com",
            tags=["later"],
            status="prospect",
        )
    )

    listing = await service.list_participants(
        PilotParticipantFilters(cohort="pilot-2025w4", tag="priority", requires_follow_up=True)
    )

    assert listing.total == 1
    assert listing.items[0].full_name == "Alice"
    assert listing.items[0].requires_follow_up is True


@pytest.mark.asyncio
async def test_update_participant_changes_status_and_metadata(feedback_session: AsyncSession) -> None:
    service = PilotParticipantService(feedback_session)
    participant = await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Casey",
            contact_email="casey@example.com",
            status="prospect",
        )
    )

    updated = await service.update_participant(
        participant.id,
        PilotParticipantUpdate(
            status="completed",
            requires_follow_up=False,
            metadata={"notes": "Completed final interview"},
            tags=["wrap-up"],
        ),
    )

    assert updated.status == "completed"
    assert updated.metadata == {"notes": "Completed final interview"}
    assert updated.tags == ["wrap-up"]


@pytest.mark.asyncio
async def test_upsert_participant_updates_existing_record(feedback_session: AsyncSession) -> None:
    service = PilotParticipantService(feedback_session)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Taylor",
            contact_email="taylor@example.com",
            status="prospect",
            requires_follow_up=True,
            tags=["priority"],
        )
    )

    payload = PilotParticipantCreate(
        cohort="pilot-2025w4",
        full_name="Taylor Lee",
        contact_email="taylor@example.com",
        status="invited",
        requires_follow_up=False,
        tags=["priority", "demo"],
    )
    updated, created_flag = await service.upsert_participant(payload)

    assert created_flag is False
    assert updated.status == "invited"
    assert updated.requires_follow_up is False
    assert updated.tags == ["priority", "demo"]
    assert updated.full_name == "Taylor Lee"


@pytest.mark.asyncio
async def test_summarize_participants_groups_by_status(feedback_session: AsyncSession) -> None:
    service = PilotParticipantService(feedback_session)
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Alex",
            contact_email="alex@example.com",
            status="prospect",
            invited_at=datetime.utcnow(),
            tags=["android", "voice"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Jamie",
            contact_email="jamie@example.com",
            status="invited",
            requires_follow_up=True,
            tags=["voice"],
        )
    )
    await service.create_participant(
        PilotParticipantCreate(
            cohort="pilot-2025w4",
            full_name="Morgan",
            contact_email="morgan@example.com",
            status="onboarded",
            onboarded_at=datetime.utcnow(),
            consent_signed_at=datetime.utcnow(),
            tags=["ios"],
        )
    )

    summary = await service.summarize_participants(
        PilotParticipantFilters(cohort="pilot-2025w4")
    )

    assert summary.cohort == "pilot-2025w4"
    assert summary.total == 3
    assert summary.status_breakdown["prospect"] == 1
    assert summary.status_breakdown["invited"] == 1
    assert summary.status_breakdown["onboarded"] == 1
    assert summary.pending_invites == 2
    assert summary.requires_follow_up == 1
    assert summary.invited >= 1
    assert summary.consented == 1
    assert summary.onboarded == 1
    assert summary.tag_totals["voice"] == 2
    assert summary.with_contact_methods == 3
    assert summary.last_activity_at is not None


@pytest.mark.asyncio
async def test_record_feedback_with_missing_participant_raises(feedback_session: AsyncSession) -> None:
    service = PilotFeedbackService(feedback_session)

    with pytest.raises(ValueError):
        await service.record_feedback(
            PilotFeedbackCreate(
                cohort="pilot-2025w4",
                participant_id=UUID("12345678-1234-5678-1234-567812345678"),
                channel="web",
                role="participant",
                sentiment_score=3,
                trust_score=3,
                usability_score=3,
                tags=["invalid"],
            )
        )


@pytest.mark.asyncio
async def test_generate_backlog_prioritises_high_impact_groups(
    feedback_session: AsyncSession,
) -> None:
    service = PilotFeedbackService(feedback_session)
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            channel="web",
            role="participant",
            sentiment_score=2,
            trust_score=2,
            usability_score=2,
            severity="critical",
            tags=["latency"],
            blockers="Streaming froze during session.",
            follow_up_needed=True,
        )
    )
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            channel="mobile",
            role="participant",
            sentiment_score=3,
            trust_score=3,
            usability_score=3,
            severity="medium",
            tags=["latency"],
            highlights="Improved after reconnect.",
        )
    )
    await service.record_feedback(
        PilotFeedbackCreate(
            cohort="pilot-2025w4",
            channel="web",
            role="participant",
            sentiment_score=5,
            trust_score=5,
            usability_score=5,
            severity="low",
            tags=["delight"],
            highlights="Voice playback felt natural.",
        )
    )

    backlog = await service.generate_backlog(PilotFeedbackFilters(cohort="pilot-2025w4"), limit=5)

    assert backlog.total == 2
    assert backlog.items[0].label == "latency"
    assert backlog.items[0].representative_severity == "critical"
    assert backlog.items[0].follow_up_count == 1
    assert backlog.items[0].frequency == 2
    assert backlog.items[0].average_sentiment < backlog.items[1].average_sentiment
    assert backlog.items[0].priority_score > backlog.items[1].priority_score
