from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.sqltypes import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.models.entities import (
    AnalyticsEvent,
    ChatMessage,
    ChatSession,
    ConversationMemory,
    DailySummary,
    LoginChallenge,
    RefreshToken,
    User,
)
from app.services.data_subject import DataSubjectService, StorageRetentionClient


class RecordingStorage(StorageRetentionClient):
    def __init__(self, transcript_objects: int = 0, summary_objects: int = 0) -> None:
        self.transcript_calls: list[list[UUID]] = []
        self.summary_calls: list[UUID] = []
        self.transcript_objects = transcript_objects
        self.summary_objects = summary_objects

    async def delete_transcripts(self, session_ids):
        self.transcript_calls.append(list(session_ids))
        return self.transcript_objects

    async def delete_summaries(self, user_id):
        self.summary_calls.append(user_id)
        return self.summary_objects


@pytest_asyncio.fixture()
async def sar_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(ChatSession.__table__.create)
        await conn.run_sync(ChatMessage.__table__.create)
        await conn.run_sync(DailySummary.__table__.create)
        await conn.run_sync(ConversationMemory.__table__.create)
        await conn.run_sync(RefreshToken.__table__.create)
        await conn.run_sync(AnalyticsEvent.__table__.create)
        await conn.run_sync(LoginChallenge.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


def make_service(session: AsyncSession, storage: RecordingStorage | None = None) -> tuple[DataSubjectService, RecordingStorage]:
    settings = AppSettings(APP_ENV="test")
    storage_client = storage or RecordingStorage()
    service = DataSubjectService(session, settings, storage_client=storage_client)
    return service, storage_client


@pytest.mark.asyncio
async def test_export_user_data_compiles_related_records(sar_session: AsyncSession) -> None:
    service, _ = make_service(sar_session)

    user_id = uuid4()
    user = User(
        id=user_id,
        email="patient@example.com",
        phone_number="+8613800138000",
        display_name="测试用户",
        locale="zh-CN",
        timezone="Asia/Shanghai",
    )
    chat_session = ChatSession(user_id=user_id, session_state="active")
    sar_session.add_all([user, chat_session])
    await sar_session.flush()

    sar_session.add_all(
        [
            ChatMessage(
                session_id=chat_session.id,
                role="user",
                content="最近睡不好怎么办？",
                sequence_index=0,
            ),
            ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="可以尝试睡前放松练习。",
                sequence_index=1,
            ),
        ]
    )
    sar_session.add(
        DailySummary(
            user_id=user_id,
            summary_date=date.today(),
            title="给自己一点空间",
            spotlight="识别压力信号",
            summary="梳理情绪并记录触发因素。",
            mood_delta=1,
        )
    )
    sar_session.add(
        ConversationMemory(
            user_id=user_id,
            session_id=chat_session.id,
            keywords=["睡眠", "压力"],
            summary="担心工作压力影响睡眠",
            last_message_at=datetime.now(tz=timezone.utc),
        )
    )
    sar_session.add(
        AnalyticsEvent(
            user_id=user_id,
            session_id=chat_session.id,
            event_type="chat_turn_submitted",
            funnel_stage="engaged",
            properties={"turn": 1},
        )
    )
    await sar_session.commit()

    export = await service.export_user_data(user_id)

    assert export.user.email == "patient@example.com"
    assert export.user.phone_number == "+8613800138000"
    assert len(export.sessions) == 1
    assert len(export.sessions[0].messages) == 2
    assert export.daily_summaries and export.daily_summaries[0].title == "给自己一点空间"
    assert export.conversation_memories and export.conversation_memories[0].keywords == ["睡眠", "压力"]
    assert export.analytics_events and export.analytics_events[0].event_type == "chat_turn_submitted"
    assert export.weekly_summaries == []


@pytest.mark.asyncio
async def test_delete_user_data_redacts_and_revokes_records(sar_session: AsyncSession) -> None:
    storage = RecordingStorage(transcript_objects=5, summary_objects=3)
    service, storage_client = make_service(sar_session, storage=storage)

    user_id = uuid4()
    user = User(
        id=user_id,
        email="remove@example.com",
        phone_number="+8618888888888",
        display_name="ToDelete",
        external_id="external-123",
        locale="zh-CN",
        timezone="Asia/Shanghai",
    )
    session = ChatSession(user_id=user_id, session_state="active")
    sar_session.add_all([user, session])
    await sar_session.flush()

    sar_session.add_all(
        [
            ChatMessage(
                session_id=session.id,
                role="user",
                content="原始内容1",
                sequence_index=0,
            ),
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content="原始内容2",
                sequence_index=1,
            ),
        ]
    )
    sar_session.add(
        DailySummary(
            user_id=user_id,
            summary_date=date.today() - timedelta(days=1),
            title="旧总结",
            spotlight="注意休息",
            summary="测试总结内容",
            mood_delta=0,
        )
    )
    sar_session.add(
        ConversationMemory(
            user_id=user_id,
            session_id=session.id,
            keywords=["测试"],
            summary="历史记忆",
            last_message_at=datetime.now(tz=timezone.utc),
        )
    )
    sar_session.add(
        AnalyticsEvent(
            user_id=user_id,
            session_id=session.id,
            event_type="chat_turn_submitted",
            properties={"turn": 1},
        )
    )
    sar_session.add(
        RefreshToken(
            user_id=user_id,
            token_hash="token-hash",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=30),
        )
    )
    sar_session.add(
        LoginChallenge(
            user_id=user_id,
            provider="sms",
            phone_number="+8618888888888",
            code_hash="code",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        )
    )
    await sar_session.commit()

    report = await service.delete_user_data(user_id, redaction_token="[removed]")
    await sar_session.commit()

    assert report.messages_redacted == 2
    assert report.sessions_impacted == 1
    assert report.daily_summaries_deleted == 1
    assert report.weekly_summaries_deleted == 0
    assert report.memories_deleted == 1
    assert report.analytics_anonymised == 1
    assert report.refresh_tokens_revoked == 1
    assert report.transcripts_deleted == 5
    assert report.summary_objects_deleted == 3
    assert sorted(report.pii_fields_cleared) == [
        "display_name",
        "email",
        "external_id",
        "phone_number",
    ]

    refreshed_user = await sar_session.get(User, user_id)
    assert refreshed_user is not None
    assert refreshed_user.email is None
    assert refreshed_user.phone_number is None
    assert refreshed_user.external_id is None
    assert refreshed_user.display_name is None

    messages = (
        await sar_session.execute(
            select(ChatMessage.content).where(ChatMessage.session_id == session.id)
        )
    ).scalars().all()
    assert messages == ["[removed]", "[removed]"]

    remaining_summaries = (
        await sar_session.execute(
            select(DailySummary).where(DailySummary.user_id == user_id)
        )
    ).scalars().all()
    assert remaining_summaries == []

    remaining_memories = (
        await sar_session.execute(
            select(ConversationMemory).where(ConversationMemory.user_id == user_id)
        )
    ).scalars().all()
    assert remaining_memories == []

    remaining_tokens = (
        await sar_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
    ).scalars().all()
    assert remaining_tokens == []

    anonymised_event = (
        await sar_session.execute(select(AnalyticsEvent))
    ).scalars().first()
    assert anonymised_event is not None
    assert anonymised_event.user_id is None
    assert anonymised_event.session_id is None
    assert "anonymised_at" in anonymised_event.properties

    login_challenge = await sar_session.execute(
        select(LoginChallenge).where(LoginChallenge.user_id == user_id)
    )
    challenge = login_challenge.scalars().first()
    assert challenge is not None
    assert challenge.phone_number is None
    assert challenge.payload is None

    assert storage_client.transcript_calls == [[session.id]]
    assert storage_client.summary_calls == [user_id]
@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"

ConversationMemory.__table__.c.keywords.type = JSON()
