from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import PilotFeedback, User
from app.schemas.feedback import PilotFeedbackCreate, PilotFeedbackFilters
from app.services.feedback import PilotFeedbackService


@pytest_asyncio.fixture()
async def feedback_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
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
async def test_summarize_feedback_returns_metrics(feedback_session: AsyncSession) -> None:
    service = PilotFeedbackService(feedback_session)
    now = datetime.now(timezone.utc)
    entries = [
        PilotFeedback(
            cohort="pilot-2025w4",
            channel="mobile",
            role="participant",
            scenario="chat",
            sentiment_score=5,
            trust_score=4,
            usability_score=4,
            severity="high",
            tags=["latency", "voice"],
            highlights="Voice playback felt natural.",
            blockers="Streaming paused twice.",
            follow_up_needed=True,
            submitted_at=now - timedelta(hours=1),
        ),
        PilotFeedback(
            cohort="pilot-2025w4",
            channel="web",
            role="therapist",
            scenario="directory",
            sentiment_score=3,
            trust_score=3,
            usability_score=5,
            severity="low",
            tags=["directory"],
            highlights="Badge copy looks polished.",
            blockers=None,
            follow_up_needed=False,
            submitted_at=now - timedelta(days=1),
        ),
    ]
    feedback_session.add_all(entries)
    await feedback_session.flush()

    report = await service.summarize_feedback(
        PilotFeedbackFilters(cohort="pilot-2025w4"), highlight_limit=3
    )

    assert report.total_entries == 2
    assert report.average_scores.average_sentiment == 4.0
    assert report.average_scores.tone_support_rate == 50.0
    assert report.severity_breakdown["high"] == 1
    assert report.channel_breakdown["mobile"] == 1
    assert report.follow_up_required == 1
    assert report.tag_frequency[0].tag == "latency"
    assert len(report.recent_highlights) == 2
    assert report.blocker_insights[0].blockers == "Streaming paused twice."


@pytest.mark.asyncio
async def test_summarize_feedback_respects_date_filters(feedback_session: AsyncSession) -> None:
    service = PilotFeedbackService(feedback_session)
    now = datetime.now(timezone.utc)
    older = PilotFeedback(
        cohort="pilot-2025w4",
        channel="mobile",
        role="participant",
        sentiment_score=5,
        trust_score=5,
        usability_score=5,
        tags=["delight"],
        submitted_at=now - timedelta(days=10),
    )
    recent = PilotFeedback(
        cohort="pilot-2025w4",
        channel="mobile",
        role="participant",
        sentiment_score=2,
        trust_score=2,
        usability_score=2,
        tags=["latency"],
        submitted_at=now - timedelta(days=1),
    )
    feedback_session.add_all([older, recent])
    await feedback_session.flush()

    filters = PilotFeedbackFilters(
        cohort="pilot-2025w4",
        submitted_since=now - timedelta(days=2),
    )
    report = await service.summarize_feedback(filters)

    assert report.total_entries == 1
    assert report.tag_frequency[0].tag == "latency"
