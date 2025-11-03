from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from zoneinfo import ZoneInfo

from app.models.entities import MoodCheckIn, User
from app.services.mood import MoodService


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(MoodCheckIn.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as db_session:
        yield db_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_check_in_persists_and_normalizes_fields(session: AsyncSession) -> None:
    service = MoodService(session)
    user_id = uuid4()
    now = datetime(2025, 1, 3, 9, 15, tzinfo=timezone.utc)

    record = await service.create_check_in(
        user_id,
        score=4,
        energy_level=3,
        emotion=" 焦虑 ",
        tags=["睡眠", "   焦虑 ", "", "睡眠"],
        note=" 继续坚持呼吸练习 ",
        context={"trigger": "workload"},
        check_in_at=now,
    )

    assert record.id is not None
    assert record.user_id == user_id
    assert record.score == 4
    assert record.energy_level == 3
    assert set(record.tags) == {"睡眠", "焦虑"}
    assert record.note == "继续坚持呼吸练习"
    assert record.emotion == "焦虑"
    assert record.context == {"trigger": "workload"}
    assert record.check_in_at == now

    stored = await session.get(MoodCheckIn, record.id)
    assert stored is not None
    assert stored.score == 4


@pytest.mark.asyncio
async def test_list_check_ins_returns_recent_first(session: AsyncSession) -> None:
    service = MoodService(session)
    user_id = uuid4()
    await service.create_check_in(
        user_id,
        score=2,
        check_in_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    await service.create_check_in(
        user_id,
        score=5,
        check_in_at=datetime(2025, 1, 5, 8, 0, tzinfo=timezone.utc),
    )

    records = await service.list_check_ins(user_id, limit=2)
    assert len(records) == 2
    assert records[0].score == 5
    assert records[0].check_in_at > records[1].check_in_at


@pytest.mark.asyncio
async def test_summarize_returns_trend_and_streak(session: AsyncSession) -> None:
    service = MoodService(session)
    user_id = uuid4()

    user = User(id=user_id, timezone="America/Los_Angeles")
    session.add(user)
    await session.flush()

    pacific = ZoneInfo("America/Los_Angeles")
    base = datetime.now(pacific).replace(hour=9, minute=0, second=0, microsecond=0)
    timestamps = [
        base - timedelta(days=2),
        base - timedelta(days=1),
        base,
    ]
    scores = [4, 2, 5]
    for score, when in zip(scores, timestamps, strict=True):
        await service.create_check_in(
            user_id,
            score=score,
            check_in_at=when,
        )

    summary = await service.summarize(user_id, window_days=5)

    expected_average = sum(scores) / len(scores)
    assert pytest.approx(summary.average_score, rel=1e-3) == expected_average
    assert summary.sample_count == len(scores)
    assert summary.streak_days == 1
    assert summary.last_check_in is not None
    assert summary.last_check_in.score == 5
    assert len(summary.trend) == len(scores)
    assert summary.trend[0].date == timestamps[0].date()
    assert summary.trend[-1].average_score == 5.0


@pytest.mark.asyncio
async def test_summarize_returns_empty_with_last_reference(session: AsyncSession) -> None:
    service = MoodService(session)
    user_id = uuid4()

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    await service.create_check_in(user_id, score=3, check_in_at=thirty_days_ago)

    summary = await service.summarize(user_id, window_days=7)
    assert summary.sample_count == 0
    assert summary.trend == []
    assert summary.last_check_in is not None
    assert summary.last_check_in.score == 3


@pytest.mark.asyncio
async def test_create_check_in_validates_ranges(session: AsyncSession) -> None:
    service = MoodService(session)
    user_id = uuid4()

    with pytest.raises(ValueError):
        await service.create_check_in(user_id, score=0)

    with pytest.raises(ValueError):
        await service.create_check_in(user_id, score=3, energy_level=7)
