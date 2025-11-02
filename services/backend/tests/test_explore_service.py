from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.models.entities import FeatureFlag
from app.schemas.explore import ExploreModuleType
from app.schemas.reports import DailyReport, JourneyReportsResponse, WeeklyReport
from app.services.explore import ExploreService
from app.services.feature_flags import FeatureFlagService


class StubReportsService:
    def __init__(self, payload: JourneyReportsResponse) -> None:
        self.payload = payload
        self.calls: list[str] = []

    async def get_reports(self, user_id: str) -> JourneyReportsResponse:
        self.calls.append(user_id)
        return self.payload


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(FeatureFlag.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        yield session

    await engine.dispose()


def make_reports_payload() -> JourneyReportsResponse:
    return JourneyReportsResponse(
        daily=[
            DailyReport(
                report_date=date(2025, 1, 6),
                title="今日回顾",
                spotlight="继续保持 4-7-8 呼吸，焦虑指数下降。",
                summary="近期关注焦虑管理与睡眠节律。",
                mood_delta=1,
            )
        ],
        weekly=[
            WeeklyReport(
                week_start=date(2025, 1, 6),
                themes=["压力管理", "睡眠节律"],
                highlights="坚持晚间放松训练，入睡时间提前 10 分钟。",
                action_items=["保持呼吸练习", "记录睡前情绪"],
                risk_level="low",
            )
        ],
        conversations=[],
    )


@pytest.mark.asyncio
async def test_build_modules_includes_all_enabled_categories(session: AsyncSession) -> None:
    settings = AppSettings(
        **{"FEATURE_FLAGS": '{"explore_breathing": true, "explore_psychoeducation": true, "explore_trending": true}'}
    )
    feature_flags = FeatureFlagService(session, settings)
    reports_service = StubReportsService(make_reports_payload())
    service = ExploreService(feature_flags, reports_service)

    payload = await service.build_modules(user_id=str(uuid4()), locale="zh-CN")

    module_types = {module.module_type for module in payload.modules}
    assert module_types == {
        ExploreModuleType.BREATHING_EXERCISE,
        ExploreModuleType.PSYCHOEDUCATION,
        ExploreModuleType.TRENDING_TOPICS,
    }

    trending = next(
        module for module in payload.modules if module.module_type == ExploreModuleType.TRENDING_TOPICS
    )
    assert trending.topics, "Trending module should include derived topics."
    assert trending.topics[0].name == "压力管理"
    assert "呼吸" in trending.insights[0]
    assert reports_service.calls, "Reports service should be invoked for personalization."


@pytest.mark.asyncio
async def test_disabled_feature_flag_excludes_module(session: AsyncSession) -> None:
    settings = AppSettings(
        **{"FEATURE_FLAGS": '{"explore_breathing": true, "explore_psychoeducation": true, "explore_trending": true}'}
    )
    feature_flags = FeatureFlagService(session, settings)
    reports_service = StubReportsService(make_reports_payload())
    service = ExploreService(feature_flags, reports_service)

    await session.execute(
        FeatureFlag.__table__.insert().values(
            key="explore_psychoeducation",
            enabled=False,
            rollout_percentage=100,
            description="Temporarily disabled in test.",
        )
    )
    await session.commit()

    payload = await service.build_modules(user_id=str(uuid4()), locale="en-US")

    module_types = {module.module_type for module in payload.modules}
    assert ExploreModuleType.PSYCHOEDUCATION not in module_types
    assert payload.evaluated_flags["explore_psychoeducation"] is False
    assert payload.locale == "en-US"
