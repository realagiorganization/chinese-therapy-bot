from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import ChatMessage, ChatSession, User
from app.schemas.chat import ChatRequest
from app.schemas.therapists import TherapistRecommendation
from app.services.chat import ChatService


class StubOrchestrator:
    """Deterministic orchestrator used for unit tests."""

    async def generate_reply(self, history, *, language: str = "zh-CN", context_prompt=None):
        return "感谢你的分享，让我们一起做一次呼吸练习。"

    async def stream_reply(self, history, *, language: str = "zh-CN", context_prompt=None):
        for fragment in ["感谢", "你的分享"]:
            yield fragment


class StubTranscriptStorage:
    def __init__(self) -> None:
        self.persist_calls: list[dict[str, object]] = []

    async def persist_transcript(self, *, session_id: UUID, user_id: UUID, messages):
        self.persist_calls.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "messages": messages,
            }
        )
        return "transcripts/test.json"


class StubMemoryService:
    def __init__(self) -> None:
        self.captured: list[dict[str, object]] = []

    async def list_memories(self, user_id, *, limit: int = 5):
        return [
            SimpleNamespace(summary="最近关注焦虑管理。", keywords=["焦虑", "压力"]),
        ]

    async def capture(self, **kwargs):
        self.captured.append(kwargs)


class StubRecommendationService:
    async def recommend(self, query: str, *, locale: str, limit: int = 3):
        return [
            TherapistRecommendation(
                therapist_id="00000000-0000-0000-0000-000000000111",
                name="刘心语",
                title="注册心理咨询师",
                specialties=["焦虑管理"],
                languages=["zh-CN"],
                price_per_session=680.0,
                currency="CNY",
                is_recommended=True,
                score=0.92,
                reason="匹配焦虑主题。",
                matched_keywords=["焦虑"],
            )
        ]


@pytest_asyncio.fixture()
async def chat_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(ChatSession.__table__.create)
        await conn.run_sync(ChatMessage.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_stream_turn_emits_events_and_persists_transcript(chat_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubTranscriptStorage()
    memory = StubMemoryService()
    recommendations = StubRecommendationService()

    service = ChatService(
        chat_session,
        orchestrator,
        storage,
        memory_service=memory,
        recommendation_service=recommendations,
    )

    payload = ChatRequest(
        user_id=uuid4(),
        message="我最近焦虑很厉害，晚上睡不着。",
        locale="zh-CN",
        session_id=None,
        enable_streaming=True,
    )

    events = []
    async for event in service.stream_turn(payload):
        events.append(event)

    assert events, "Expected at least one SSE event."
    assert events[0]["event"] == "session_established"
    token_events = [event for event in events if event["event"] == "token"]
    assert token_events, "Expected streaming token events."
    assert token_events[0]["data"]["delta"] == "感谢"
    assert events[-1]["event"] == "complete"
    assert events[-1]["data"]["message"]["content"].startswith("感谢你的分享")
    assert events[-1]["data"]["recommendations"]
    assert events[-1]["data"]["memory_highlights"]

    assert storage.persist_calls
    persisted_messages = storage.persist_calls[0]["messages"]
    assert len(persisted_messages) == 2
    assert persisted_messages[0]["role"] == "user"
    assert persisted_messages[1]["role"] == "assistant"

    assert memory.captured

    # Verify chat messages were stored in the database for historical replay.
    db_messages = await chat_session.execute(select(ChatMessage))
    stored = db_messages.scalars().all()
    assert len(stored) == 2
