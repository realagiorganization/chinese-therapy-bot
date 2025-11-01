from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppSettings
from app.integrations.llm import ChatOrchestrator
from app.integrations.storage import SummaryStorage
from app.models import ChatMessage as ChatMessageModel
from app.models import ChatSession, DailySummary, User, WeeklySummary


logger = logging.getLogger(__name__)


class SummaryGenerationService:
    """Generate and persist daily/weekly summaries for a MindWell user."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppSettings,
        orchestrator: ChatOrchestrator,
        storage: SummaryStorage | None = None,
    ):
        self._session = session
        self._settings = settings
        self._orchestrator = orchestrator
        self._storage = storage

    async def generate_daily_summary(
        self,
        user_id: UUID,
        *,
        target_date: date | None = None,
    ) -> DailySummary | None:
        target = target_date or date.today()
        start, end = self._daily_window(target)

        messages = await self._load_messages(user_id, start, end)
        if not messages:
            logger.info("No chat activity for user %s on %s; skipping daily summary.", user_id, target)
            return None

        user = await self._session.get(User, user_id)
        locale = user.locale if user and user.locale else "zh-CN"

        summary_payload = await self._summarize_conversation(
            messages,
            summary_type="daily",
            locale=locale,
        )

        mood_delta = self._estimate_mood_delta(messages)
        existing = await self._get_daily_summary(user_id, target)
        if existing:
            existing.title = summary_payload["title"]
            existing.spotlight = summary_payload["spotlight"]
            existing.summary = summary_payload["summary"]
            existing.mood_delta = mood_delta
            record = existing
        else:
            record = DailySummary(
                user_id=user_id,
                summary_date=target,
                title=summary_payload["title"],
                spotlight=summary_payload["spotlight"],
                summary=summary_payload["summary"],
                mood_delta=mood_delta,
            )
            self._session.add(record)

        await self._session.flush()

        storage_payload = {
            "user_id": str(user_id),
            "summary_date": target.isoformat(),
            "title": record.title,
            "spotlight": record.spotlight,
            "summary": record.summary,
            "mood_delta": record.mood_delta,
            "source": "mindwell-summary-scheduler",
        }
        if self._storage:
            await self._storage.persist_daily_summary(
                user_id=user_id,
                summary_date=target,
                payload=storage_payload,
            )

        return record

    async def generate_weekly_summary(
        self,
        user_id: UUID,
        *,
        anchor_date: date | None = None,
    ) -> WeeklySummary | None:
        anchor = anchor_date or date.today()
        week_start = anchor - timedelta(days=anchor.weekday())
        start = datetime.combine(week_start, time.min)
        end = start + timedelta(days=7)

        messages = await self._load_messages(user_id, start, end)
        if not messages:
            logger.info("No chat activity for user %s during week %s; skipping weekly summary.", user_id, week_start)
            return None

        user = await self._session.get(User, user_id)
        locale = user.locale if user and user.locale else "zh-CN"

        summary_payload = await self._summarize_conversation(
            messages,
            summary_type="weekly",
            locale=locale,
        )

        existing = await self._get_weekly_summary(user_id, week_start)
        if existing:
            existing.themes = summary_payload["themes"]
            existing.highlights = summary_payload["highlights"]
            existing.action_items = summary_payload["action_items"]
            existing.risk_level = summary_payload["risk_level"]
            record = existing
        else:
            record = WeeklySummary(
                user_id=user_id,
                week_start=week_start,
                themes=summary_payload["themes"],
                highlights=summary_payload["highlights"],
                action_items=summary_payload["action_items"],
                risk_level=summary_payload["risk_level"],
            )
            self._session.add(record)

        await self._session.flush()

        storage_payload = {
            "user_id": str(user_id),
            "week_start": week_start.isoformat(),
            "themes": record.themes,
            "highlights": record.highlights,
            "action_items": record.action_items,
            "risk_level": record.risk_level,
            "source": "mindwell-summary-scheduler",
        }
        if self._storage:
            await self._storage.persist_weekly_summary(
                user_id=user_id,
                week_start=week_start,
                payload=storage_payload,
            )

        return record

    async def active_user_ids_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[UUID]:
        stmt: Select[tuple[UUID]] = (
            select(ChatSession.user_id)
            .join(ChatMessageModel, ChatMessageModel.session_id == ChatSession.id)
            .where(ChatMessageModel.created_at >= start)
            .where(ChatMessageModel.created_at < end)
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def _load_messages(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[ChatMessageModel]:
        stmt = (
            select(ChatMessageModel)
            .join(ChatSession, ChatMessageModel.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .where(ChatMessageModel.created_at >= start)
            .where(ChatMessageModel.created_at < end)
            .order_by(ChatMessageModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _get_daily_summary(
        self,
        user_id: UUID,
        summary_date: date,
    ) -> DailySummary | None:
        stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .where(DailySummary.summary_date == summary_date)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_weekly_summary(
        self,
        user_id: UUID,
        week_start: date,
    ) -> WeeklySummary | None:
        stmt = (
            select(WeeklySummary)
            .where(WeeklySummary.user_id == user_id)
            .where(WeeklySummary.week_start == week_start)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _summarize_conversation(
        self,
        messages: Iterable[ChatMessageModel],
        *,
        summary_type: str,
        locale: str,
    ) -> dict[str, Any]:
        history = [
            {
                "role": "assistant" if message.role != "user" else "user",
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else "",
            }
            for message in messages
        ]

        try:
            return await self._orchestrator.summarize_conversation(
                history,
                summary_type=summary_type,
                language=locale,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("LLM summarization failed; falling back to heuristic summary.", exc_info=exc)
            return self._heuristic_summary(history, summary_type=summary_type, locale=locale)

    def _heuristic_summary(
        self,
        history: list[dict[str, Any]],
        *,
        summary_type: str,
        locale: str,
    ) -> dict[str, Any]:
        """Fallback summary leveraging keyword frequency analysis."""
        user_messages = [item["content"] for item in history if item["role"] == "user"]
        keywords = Counter()
        for message in user_messages:
            for token in ("焦虑", "压力", "睡眠", "关系", "家庭", "工作", "放松", "希望"):
                if token in message:
                    keywords[token] += 1

        top_keywords = [token for token, _ in keywords.most_common(3)]
        highlight = "、".join(top_keywords) if top_keywords else "情绪调整"

        if summary_type == "daily":
            title = f"{self._settings.app_env.upper()} 日常回顾" if locale.startswith("zh") else "MindWell Daily Reflection"
            spotlight = f"今日关注：{highlight}" if locale.startswith("zh") else f"Focus today: {highlight}"
            summary = (
                "用户分享了持续关注的主题，建议安排一次呼吸练习并记录情绪变化。"
                if locale.startswith("zh")
                else "The user focused on emotional regulation. Suggest scheduling a breathing exercise and journaling."
            )
            return {
                "title": title,
                "spotlight": spotlight,
                "summary": summary,
            }

        themes = top_keywords or ["情绪管理" if locale.startswith("zh") else "Emotional regulation"]
        highlights = (
            "本周持续练习正念，情绪起伏趋于稳定。"
            if locale.startswith("zh")
            else "Mindfulness practice continued this week, leading to steadier emotions."
        )
        action_items = [
            "保持每日两次深呼吸练习" if locale.startswith("zh") else "Maintain twice-daily breathing practice",
            "记录一次令你充电的活动" if locale.startswith("zh") else "Log one energizing activity",
        ]
        return {
            "themes": themes,
            "highlights": highlights,
            "action_items": action_items,
            "risk_level": "medium" if "焦虑" in top_keywords else "low",
        }

    def _estimate_mood_delta(self, messages: Iterable[ChatMessageModel]) -> int:
        positive_tokens = ("放松", "感谢", "开心", "希望", "改善", "轻松")
        negative_tokens = ("焦虑", "压力", "难受", "沮丧", "疲惫", "失眠")

        score = 0
        for message in messages:
            if message.role != "user":
                continue
            content = message.content
            score += sum(1 for token in positive_tokens if token in content)
            score -= sum(1 for token in negative_tokens if token in content)

        return max(-3, min(3, score))

    def _daily_window(self, target: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target, time.min)
        end = start + timedelta(days=1)
        return start, end


class SummaryScheduler:
    """Coordinate summary generation across all active users."""

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._orchestrator = ChatOrchestrator(settings)
        self._storage = SummaryStorage(settings)

    async def run_daily(self, *, target_date: date | None = None) -> int:
        from app.core.database import init_database, session_scope

        await init_database()
        generated = 0
        async with session_scope() as session:
            service = SummaryGenerationService(
                session,
                self._settings,
                self._orchestrator,
                self._storage,
            )
            target = target_date or date.today()
            start, end = service._daily_window(target)
            user_ids = await service.active_user_ids_between(start, end)
            for user_id in user_ids:
                record = await service.generate_daily_summary(user_id, target_date=target)
                if record:
                    generated += 1
        return generated

    async def run_weekly(self, *, anchor_date: date | None = None) -> int:
        from app.core.database import init_database, session_scope

        await init_database()
        generated = 0
        async with session_scope() as session:
            service = SummaryGenerationService(
                session,
                self._settings,
                self._orchestrator,
                self._storage,
            )
            anchor = anchor_date or date.today()
            week_start = anchor - timedelta(days=anchor.weekday())
            start = datetime.combine(week_start, time.min)
            end = start + timedelta(days=7)
            user_ids = await service.active_user_ids_between(start, end)
            for user_id in user_ids:
                record = await service.generate_weekly_summary(user_id, anchor_date=anchor)
                if record:
                    generated += 1
        return generated
