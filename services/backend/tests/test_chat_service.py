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
from app.services.knowledge_base import KnowledgeBaseEntry


class StubOrchestrator:
    """Deterministic orchestrator used for unit tests."""

    def __init__(self) -> None:
        self.last_context_prompt = None

    async def generate_reply(self, history, *, language: str = "zh-CN", context_prompt=None):
        self.last_context_prompt = context_prompt
        return "感谢你的分享，让我们一起做一次呼吸练习。"

    async def stream_reply(self, history, *, language: str = "zh-CN", context_prompt=None):
        self.last_context_prompt = context_prompt
        for fragment in ["感谢", "你的分享"]:
            yield fragment


class StubTranscriptStorage:
    def __init__(self) -> None:
        self.persist_calls: list[dict[str, object]] = []
        self.message_calls: list[dict[str, object]] = []

    async def persist_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        sequence_index: int,
        role: str,
        content: str,
        created_at,
    ):
        self.message_calls.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "sequence_index": sequence_index,
                "role": role,
                "content": content,
                "created_at": created_at,
            }
        )
        return f"conversations/{session_id}/stream/{sequence_index}.json"

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


class StubKnowledgeBaseService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(self, query: str, *, locale: str, limit: int = 3):
        self.calls.append({"query": query, "locale": locale, "limit": limit})
        return [
            KnowledgeBaseEntry(
                entry_id="sleep_regulation_cn",
                locale="zh-CN",
                title="重建睡眠节奏的三个关键动作",
                summary="规律睡眠节奏有助于缓解疲惫与焦虑。",
                guidance=("晚上固定时间收尾工作，给身体“准备休息”的信号。",),
                keywords=("失眠", "睡眠"),
                tags=("sleep",),
                source="MindWell Care Team",
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
    assert events[0]["data"]["resolved_locale"] == "zh-CN"
    assert events[0]["data"]["knowledge_snippets"] == []
    token_events = [event for event in events if event["event"] == "token"]
    assert token_events, "Expected streaming token events."
    assert token_events[0]["data"]["delta"] == "感谢"
    assert events[-1]["event"] == "complete"
    assert events[-1]["data"]["message"]["content"].startswith("感谢你的分享")
    assert events[-1]["data"]["recommendations"]
    assert events[-1]["data"]["memory_highlights"]
    assert events[-1]["data"]["knowledge_snippets"] == []
    assert events[-1]["data"]["resolved_locale"] == "zh-CN"

    assert storage.persist_calls
    persisted_messages = storage.persist_calls[0]["messages"]
    assert len(persisted_messages) == 2
    assert persisted_messages[0]["role"] == "user"
    assert persisted_messages[1]["role"] == "assistant"
    assert len(storage.message_calls) == 2
    assert storage.message_calls[0]["role"] == "user"
    assert storage.message_calls[1]["role"] == "assistant"

    assert memory.captured

    # Verify chat messages were stored in the database for historical replay.
    db_messages = await chat_session.execute(select(ChatMessage))
    stored = db_messages.scalars().all()
    assert len(stored) == 2


@pytest.mark.asyncio
async def test_process_turn_includes_knowledge_snippets(chat_session: AsyncSession) -> None:
    orchestrator = StubOrchestrator()
    storage = StubTranscriptStorage()
    memory = StubMemoryService()
    recommendations = StubRecommendationService()
    knowledge = StubKnowledgeBaseService()

    service = ChatService(
        chat_session,
        orchestrator,
        storage,
        memory_service=memory,
        recommendation_service=recommendations,
        knowledge_base=knowledge,
    )

    payload = ChatRequest(
        user_id=uuid4(),
        message="最近总是睡不着，白天又很焦虑。",
        locale="zh-CN",
        session_id=None,
        enable_streaming=False,
    )

    response = await service.process_turn(payload)

    assert response.knowledge_snippets, "Expected knowledge snippets in the chat response."
    snippet = response.knowledge_snippets[0]
    assert snippet.entry_id == "sleep_regulation_cn"
    assert "睡眠" in snippet.summary
    assert orchestrator.last_context_prompt is not None
    assert "心理教育参考" in orchestrator.last_context_prompt
