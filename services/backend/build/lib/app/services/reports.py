from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ChatSession, DailySummary, WeeklySummary
from app.schemas.reports import (
    ConversationMessage,
    ConversationSlice,
    DailyReport,
    JourneyReportsResponse,
    WeeklyReport,
)


class ReportsService:
    """Summary retrieval backed by database with illustrative fallback data."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_reports(self, user_id: str) -> JourneyReportsResponse:
        user_uuid = UUID(user_id)

        daily_reports = await self._fetch_daily(user_uuid)
        weekly_reports = await self._fetch_weekly(user_uuid)
        conversations = await self._fetch_recent_conversations(user_uuid)

        if not daily_reports and not weekly_reports and not conversations:
            return self._fallback_payload()

        return JourneyReportsResponse(
            daily=daily_reports,
            weekly=weekly_reports,
            conversations=conversations,
        )

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

    async def _fetch_recent_conversations(
        self,
        user_id: UUID,
        *,
        session_limit: int = 3,
        message_limit: int = 20,
    ) -> list[ConversationSlice]:
        stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(session_limit)
        )
        result = await self._session.execute(stmt)
        sessions = result.scalars().all()
        if not sessions:
            return []

        slices: list[ConversationSlice] = []
        for session in sessions:
            ordered_messages = sorted(
                session.messages,
                key=lambda message: message.sequence_index,
            )
            trimmed = ordered_messages[-message_limit:]
            if not trimmed:
                continue

            slices.append(
                ConversationSlice(
                    session_id=str(session.id),
                    started_at=session.started_at,
                    updated_at=session.updated_at or session.started_at,
                    therapist_id=str(session.therapist_id) if session.therapist_id else None,
                    messages=[
                        ConversationMessage(
                            message_id=str(message.id),
                            role=message.role,
                            content=message.content,
                            created_at=message.created_at,
                        )
                        for message in trimmed
                    ],
                )
            )

        return slices

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

        fallback_timestamp = datetime.combine(today, datetime.min.time())
        conversation = ConversationSlice(
            session_id="00000000-0000-0000-0000-000000000001",
            started_at=fallback_timestamp,
            updated_at=fallback_timestamp,
            therapist_id=None,
            messages=[
                ConversationMessage(
                    message_id="00000000-0000-0000-0000-000000000101",
                    role="user",
                    content="最近工作压力有点大，晚上总是睡不好。",
                    created_at=fallback_timestamp,
                ),
                ConversationMessage(
                    message_id="00000000-0000-0000-0000-000000000102",
                    role="assistant",
                    content="我们先尝试一个呼吸练习，帮助身体放松，然后记录下影响睡眠的想法，好吗？",
                    created_at=fallback_timestamp,
                ),
            ],
        )

        return JourneyReportsResponse(
            daily=daily,
            weekly=weekly,
            conversations=[conversation],
        )
