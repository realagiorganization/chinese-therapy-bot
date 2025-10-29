from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailySummary, WeeklySummary
from app.schemas.reports import DailyReport, JourneyReportsResponse, WeeklyReport


class ReportsService:
    """Summary retrieval backed by database with illustrative fallback data."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_reports(self, user_id: str) -> JourneyReportsResponse:
        user_uuid = UUID(user_id)

        daily_reports = await self._fetch_daily(user_uuid)
        weekly_reports = await self._fetch_weekly(user_uuid)

        if not daily_reports and not weekly_reports:
            return self._fallback_payload()

        return JourneyReportsResponse(daily=daily_reports, weekly=weekly_reports)

    async def _fetch_daily(self, user_id: UUID) -> list[DailyReport]:
        stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .order_by(DailySummary.summary_date.desc())
            .limit(10)
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            DailyReport(
                report_date=record.summary_date,
                title=record.title,
                spotlight=record.spotlight,
                summary=record.summary,
                mood_delta=record.mood_delta,
            )
            for record in records
        ]

    async def _fetch_weekly(self, user_id: UUID) -> list[WeeklyReport]:
        stmt = (
            select(WeeklySummary)
            .where(WeeklySummary.user_id == user_id)
            .order_by(WeeklySummary.week_start.desc())
            .limit(10)
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            WeeklyReport(
                week_start=record.week_start,
                themes=record.themes or [],
                highlights=record.highlights,
                action_items=record.action_items or [],
                risk_level=record.risk_level,
            )
            for record in records
        ]

    def _fallback_payload(self) -> JourneyReportsResponse:
        today = date.today()
        daily = [
            DailyReport(
                report_date=today - timedelta(days=offset),
                title=f"第 {offset + 1} 天回顾",
                spotlight="保持呼吸练习，情绪稳定有所提升。",
                summary="用户持续进行正念练习，焦虑触发次数下降。",
                mood_delta=1,
            )
            for offset in range(3)
        ]

        weekly = [
            WeeklyReport(
                week_start=today - timedelta(days=7),
                themes=["压力管理", "睡眠质量"],
                highlights="成功建立睡前放松流程。",
                action_items=["保持睡前日记", "每周安排一次户外活动"],
                risk_level="low",
            )
        ]

        return JourneyReportsResponse(daily=daily, weekly=weekly)
