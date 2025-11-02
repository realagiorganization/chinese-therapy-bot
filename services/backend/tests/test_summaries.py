from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.models.entities import ChatMessage, ChatSession, DailySummary, User
from app.services.summaries import SummaryGenerationService


class StubOrchestrator:
    """Deterministic summarization orchestrator for unit tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.daily_counter = 0

    async def summarize_conversation(
        self,
        history: list[dict[str, object]],
        *,
        summary_type: str,
        language: str,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "summary_type": summary_type,
                "language": language,
                "message_count": len(history),
            }
        )
        if summary_type == "daily":
            self.daily_counter += 1
            return {
                "title": f"每日回顾 {self.daily_counter}",
                "spotlight": "今日关注：焦虑管理",
                "summary": "坚持呼吸练习并记录焦虑诱因。",
            }
        if summary_type == "weekly":
            return {
                "themes": ["焦虑管理", "睡眠调节"],
                "highlights": "本周呼吸练习频率提升。",
                "action_items": ["继续记录睡眠情况"],
                "risk_level": "low",
            }
        raise ValueError(f"Unexpected summary type: {summary_type}")


class StubSummaryStorage:
    """Capture persisted payloads without hitting S3."""

    def __init__(self) -> None:
        self.daily_payloads: list[dict[str, object]] = []

    async def persist_daily_summary(
        self,
        *,
        user_id: UUID,
        summary_date: date,
        payload: dict[str, object],
    ) -> str:
        record = {
            "user_id": user_id,
            "summary_date": summary_date,
            "payload": payload,
        }
        self.daily_payloads.append(record)
        return f"daily/{summary_date.isoformat()}/{user_id}.json"


@pytest_asyncio.fixture()
async def summary_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(ChatSession.__table__.create)
        await conn.run_sync(ChatMessage.__table__.create)
        await conn.run_sync(DailySummary.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_daily_summary_persists_record(summary_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubSummaryStorage()
    settings = AppSettings(APP_ENV="test")

    service = SummaryGenerationService(summary_session, settings, orchestrator, storage)

    user = User(id=uuid4(), locale="zh-CN")
    summary_session.add(user)

    chat_session = ChatSession(user_id=user.id)
    summary_session.add(chat_session)
    await summary_session.flush()

    now = datetime(2025, 1, 15, 8, 30, tzinfo=timezone.utc)
    summary_session.add_all(
        [
                ChatMessage(
                    session_id=chat_session.id,
                    role="user",
                    content="我最近焦虑很厉害，压力大到睡不着。",
                    sequence_index=1,
                    created_at=now,
                ),
            ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="让我们做一次呼吸练习。",
                sequence_index=2,
                created_at=now + timedelta(minutes=1),
            ),
        ]
    )
    await summary_session.flush()

    target = now.date()

    record = await service.generate_daily_summary(user.id, target_date=target)
    assert record is not None
    assert record.summary_date == target
    assert record.title == "每日回顾 1"
    assert record.spotlight.startswith("今日关注")
    assert record.mood_delta == -2

    assert orchestrator.calls
    first_call = orchestrator.calls[0]
    assert first_call["summary_type"] == "daily"
    assert first_call["language"] == "zh-CN"

    assert storage.daily_payloads
    stored = storage.daily_payloads[0]
    assert stored["summary_date"] == target
    assert stored["payload"]["title"] == "每日回顾 1"

    # Second invocation should update the same row instead of inserting a duplicate.
    updated = await service.generate_daily_summary(user.id, target_date=target)
    assert updated is not None
    assert updated.title == "每日回顾 2"

    result = await summary_session.execute(select(DailySummary).where(DailySummary.user_id == user.id))
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_generate_daily_summary_skips_when_no_messages(summary_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubSummaryStorage()
    settings = AppSettings(APP_ENV="test")

    service = SummaryGenerationService(summary_session, settings, orchestrator, storage)

    user = User(id=uuid4(), locale="zh-CN")
    summary_session.add(user)
    await summary_session.flush()

    record = await service.generate_daily_summary(user.id, target_date=date(2025, 1, 20))
    assert record is None
    assert storage.daily_payloads == []
    assert orchestrator.calls == []


def test_heuristic_summary_falls_back_to_keywords(summary_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubSummaryStorage()
    settings = AppSettings(APP_ENV="test")

    service = SummaryGenerationService(summary_session, settings, orchestrator, storage)

    history = [
        {"role": "user", "content": "我最近睡眠不好，还很焦虑。"},
        {"role": "assistant", "content": "尝试进行呼吸练习。"},
        {"role": "user", "content": "工作压力大，希望找到长期方法。"},
    ]

    summary = service._heuristic_summary(history, summary_type="daily", locale="zh-CN")
    assert summary["title"].startswith("TEST")  # app_env is uppercase in fallback title
    assert "焦虑" in summary["spotlight"]


def test_estimate_mood_delta_clamps_range(summary_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubSummaryStorage()
    settings = AppSettings(APP_ENV="test")

    service = SummaryGenerationService(summary_session, settings, orchestrator, storage)

    def message(content: str) -> SimpleNamespace:
        return SimpleNamespace(role="user", content=content)

    positive = [message("感谢你的帮助，我感觉轻松多了。") for _ in range(5)]
    negative = [message("我焦虑、压力大、难受又失眠。") for _ in range(5)]

    assert service._estimate_mood_delta(positive) == 3
    assert service._estimate_mood_delta(negative) == -3
