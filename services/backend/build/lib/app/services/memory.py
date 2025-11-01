from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm import ChatOrchestrator
from app.models import ConversationMemory, ChatSession, User


logger = logging.getLogger(__name__)


class ConversationMemoryService:
    """Capture and retrieve long-lived conversation memories."""

    _DEFAULT_KEYWORDS: tuple[str, ...] = (
        "焦虑",
        "压力",
        "失眠",
        "抑郁",
        "恐慌",
        "恐惧",
        "孤独",
        "愤怒",
        "悲伤",
        "家庭",
        "婚姻",
        "关系",
        "孩子",
        "学习",
        "工作",
        "健康",
        "自信",
        "睡眠",
        "career",
        "anxiety",
        "stress",
        "insomnia",
        "depression",
        "family",
        "relationship",
    )

    def __init__(
        self,
        session: AsyncSession,
        orchestrator: ChatOrchestrator,
        *,
        keywords: Iterable[str] | None = None,
        max_messages: int = 20,
    ):
        self._session = session
        self._orchestrator = orchestrator
        self._keywords = tuple(sorted(set(keywords)) if keywords else self._DEFAULT_KEYWORDS)
        self._max_messages = max(5, max_messages)

    async def capture(
        self,
        *,
        user: User,
        session: ChatSession,
        history: Sequence[dict[str, str]],
    ) -> ConversationMemory | None:
        """Capture a memory slice when keywords of interest are detected."""
        keyword_hits = self._extract_keywords(history)
        if not keyword_hits:
            return None

        trimmed_history = self._trim_history(history)
        if not trimmed_history:
            return None

        locale = user.locale if getattr(user, "locale", None) else "zh-CN"
        summary_payload = await self._summarize(trimmed_history, keyword_hits, locale=locale)
        summary_text = summary_payload.get("summary") or summary_payload.get("memory") or ""
        derived_keywords = self._coalesce_keywords(summary_payload.get("keywords"), fallback=keyword_hits)

        if not summary_text:
            logger.debug("Memory summarization produced empty text; skipping capture.")
            return None

        last_timestamp = self._extract_timestamp(trimmed_history[-1])

        existing = await self._get_by_session(session.id)
        if existing:
            merged_keywords = sorted(set((existing.keywords or []) + derived_keywords))
            existing.keywords = merged_keywords
            existing.summary = summary_text
            existing.last_message_at = last_timestamp
            await self._session.flush()
            return existing

        record = ConversationMemory(
            user_id=user.id,
            session_id=session.id,
            keywords=sorted(set(derived_keywords)),
            summary=summary_text,
            last_message_at=last_timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_memories(
        self,
        user_id: str | UUID,
        *,
        limit: int = 20,
    ) -> list[ConversationMemory]:
        """Return stored memories ordered by recency."""
        user_uuid = self._coerce_uuid(user_id)
        stmt = (
            select(ConversationMemory)
            .where(ConversationMemory.user_id == user_uuid)
            .order_by(ConversationMemory.last_message_at.desc())
            .limit(max(1, limit))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _get_by_session(self, session_id: UUID | None) -> ConversationMemory | None:
        if session_id is None:
            return None

        stmt = select(ConversationMemory).where(ConversationMemory.session_id == session_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _summarize(
        self,
        history: Sequence[dict[str, str]],
        keyword_hits: Sequence[str],
        *,
        locale: str,
    ) -> dict[str, str | list[str]]:
        try:
            return await self._orchestrator.summarize_conversation(
                list(history),
                summary_type="memory",
                language=locale,
                max_tokens=384,
            )
        except RuntimeError:
            logger.debug("Falling back to heuristic memory summary due to orchestrator failure.")
            return self._heuristic_summary(history, keyword_hits, locale=locale)

    def _extract_keywords(self, history: Sequence[dict[str, str]]) -> list[str]:
        seen: set[str] = set()
        for message in history:
            role = message.get("role")
            content = (message.get("content") or "").lower()
            if role != "user" or not content:
                continue
            for keyword in self._keywords:
                if keyword.lower() in content:
                    seen.add(keyword)
        return sorted(seen)

    def _trim_history(self, history: Sequence[dict[str, str]]) -> list[dict[str, str]]:
        if not history:
            return []
        return list(history[-self._max_messages :])

    def _heuristic_summary(
        self,
        history: Sequence[dict[str, str]],
        keyword_hits: Sequence[str],
        *,
        locale: str,
    ) -> dict[str, str | list[str]]:
        user_messages = [message for message in history if message.get("role") == "user" and message.get("content")]
        focus = user_messages[-1]["content"] if user_messages else history[-1].get("content", "")
        truncated = (focus or "").strip()
        if len(truncated) > 140:
            truncated = truncated[:137].rstrip() + "..."

        keyword_text = ", ".join(keyword_hits)
        if locale.startswith("zh"):
            summary = f"用户多次提及 {keyword_text}。最近表达的重点：{truncated}"
        else:
            summary = f"The user repeatedly mentioned {keyword_text}. Latest focus: {truncated}"

        return {
            "summary": summary.strip(),
            "keywords": list(keyword_hits),
        }

    def _coalesce_keywords(
        self,
        raw_keywords: object,
        *,
        fallback: Sequence[str],
    ) -> list[str]:
        if isinstance(raw_keywords, (list, tuple, set)):
            cleaned = {str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()}
            if cleaned:
                return sorted(cleaned)
        return sorted(set(fallback))

    def _extract_timestamp(self, message: dict[str, str]) -> datetime:
        raw_ts = message.get("created_at")
        if isinstance(raw_ts, datetime):
            return raw_ts.astimezone(timezone.utc)

        if isinstance(raw_ts, str):
            normalized = raw_ts.strip()
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                logger.debug("Unable to parse timestamp '%s'; defaulting to now.", raw_ts)
        return datetime.now(tz=timezone.utc)

    def _coerce_uuid(self, value: str | UUID) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
            raise ValueError("Invalid UUID supplied for conversation memory lookup.") from exc
