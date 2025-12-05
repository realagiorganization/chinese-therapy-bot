from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import AnalyticsEvent, ChatSession, User
from app.schemas.analytics import AnalyticsEventCreate
from app.services.analytics import AnalyticsEventType, ProductAnalyticsService


@pytest_asyncio.fixture()
async def analytics_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(ChatSession.__table__.create)
        await conn.run_sync(AnalyticsEvent.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_record_event_stores_payload(analytics_session: AsyncSession) -> None:
    service = ProductAnalyticsService(analytics_session)
    payload = AnalyticsEventCreate(event_type="custom-event", properties={"foo": "bar"})

    response = await service.record_event(payload)

    assert response.id is not None


@pytest.mark.asyncio
async def test_summarize_builds_expected_metrics(analytics_session: AsyncSession) -> None:
    service = ProductAnalyticsService(analytics_session)
    user_id = uuid4()
    session_id = uuid4()
    therapist_id = uuid4()

    await service.track_signup_event(user_id=user_id, stage=AnalyticsEventType.SIGNUP_STARTED)
    await service.track_chat_turn(
        user_id=user_id,
        session_id=session_id,
        locale="zh-CN",
        message_length=24,
    )
    await service.track_summary_view(user_id=user_id, summary_type="daily")
    await service.track_journey_report_view(user_id=user_id, report_kind="conversation_history")
    await service.track_therapist_profile_view(user_id=user_id, therapist_id=therapist_id, locale="zh-CN")
    await service.track_therapist_connect_click(
        user_id=user_id,
        therapist_id=therapist_id,
        locale="zh-CN",
        entry_point="cta",
    )
    await service.track_signup_event(user_id=user_id, stage=AnalyticsEventType.SIGNUP_COMPLETED)

    summary = await service.summarize(window_hours=1)

    assert summary.engagement.active_users == 1
    assert summary.engagement.chat_turns == 1
    assert summary.engagement.summary_views == 1
    assert summary.engagement.journey_report_views == 1
    assert summary.engagement.therapist_profile_views == 1
    assert summary.engagement.therapist_conversion_rate == 1.0
    assert summary.conversion.signup_started == 1
    assert summary.conversion.signup_completed == 1
    assert summary.conversion.signup_completion_rate == 1.0
    assert summary.conversion.therapist_connect_clicks == 1
    assert summary.conversion.therapist_connect_rate == 1.0
    assert len(summary.locale_breakdown) == 1
    assert summary.locale_breakdown[0].locale == "zh-CN"
    assert summary.locale_breakdown[0].chat_turns == 1
    assert summary.locale_breakdown[0].therapist_profile_views == 1
    assert summary.locale_breakdown[0].therapist_connect_clicks == 1


@pytest.mark.asyncio
async def test_locale_breakdown_sorts_and_limits_results(analytics_session: AsyncSession) -> None:
    service = ProductAnalyticsService(analytics_session)
    user = uuid4()
    session = uuid4()

    locales = ["zh-CN", "zh-TW", "en-US", "fr-FR", "ja-JP", "ko-KR"]
    for idx, locale in enumerate(locales, start=1):
        for _ in range(idx):
            await service.track_chat_turn(
                user_id=user,
                session_id=session,
                locale=locale,
                message_length=10,
            )
        if idx % 2 == 0:
            await service.track_therapist_profile_view(user_id=user, therapist_id=None, locale=locale)
        if idx % 3 == 0:
            await service.track_therapist_connect_click(user_id=user, therapist_id=None, locale=locale)

    summary = await service.summarize(window_hours=4)

    assert len(summary.locale_breakdown) == 5  # default limit
    assert summary.locale_breakdown[0].locale == "ko-KR"
    assert summary.locale_breakdown[0].chat_turns == len(locales)
    assert all(item.locale != "zh-CN" for item in summary.locale_breakdown)
