from datetime import date, timedelta

from app.schemas.reports import DailyReport, JourneyReportsResponse, WeeklyReport


class ReportsService:
    """Summary retrieval with placeholder data."""

    async def get_reports(self, user_id: str) -> JourneyReportsResponse:
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
                action_items=[
                    "保持睡前日记",
                    "每周安排一次户外活动",
                ],
                risk_level="low",
            )
        ]

        return JourneyReportsResponse(daily=daily, weekly=weekly)
