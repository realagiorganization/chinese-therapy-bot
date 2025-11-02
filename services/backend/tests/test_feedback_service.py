from __future__ import annotations

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
