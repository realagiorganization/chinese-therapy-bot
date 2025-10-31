from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from uuid import UUID
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm import ChatOrchestrator
from app.integrations.storage import ChatTranscriptStorage
from app.models import ChatMessage as ChatMessageModel
from app.models import ChatSession, Therapist, User
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.memory import ConversationMemoryService


logger = logging.getLogger(__name__)


class ChatService:
    """Chat orchestration coordinating persistence, LLM responses, and transcript storage."""

    def __init__(
        self,
        session: AsyncSession,
        orchestrator: ChatOrchestrator,
        storage: ChatTranscriptStorage,
        memory_service: ConversationMemoryService | None = None,
    ):
        self._session = session
        self._orchestrator = orchestrator
        self._storage = storage
        self._memory = memory_service

    async def process_turn(self, payload: ChatRequest) -> ChatResponse:
        context = await self._prepare_turn(payload)
        reply_text = await self._orchestrator.generate_reply(
            context["history"], language=payload.locale
        )

        assistant_message = await self._append_message(
            context["chat_session"],
            role="assistant",
            content=reply_text,
        )

        history = await self._persist_transcript(context["chat_session"], context["user"].id)
        await self._capture_memory(
            user=context["user"],
            chat_session=context["chat_session"],
            history=history,
        )

        return ChatResponse(
            session_id=context["chat_session"].id,
            reply=ChatMessage.model_validate(assistant_message),
            recommended_therapist_ids=context["recommended_ids"],
        )

    async def stream_turn(self, payload: ChatRequest) -> AsyncIterator[dict[str, Any]]:
        context = await self._prepare_turn(payload)

        yield {
            "event": "session_established",
            "data": {
                "session_id": str(context["chat_session"].id),
                "recommended_therapist_ids": context["recommended_ids"],
            },
        }

        reply_fragments: list[str] = []
        async for delta in self._orchestrator.stream_reply(
            context["history"], language=payload.locale
        ):
            if not delta:
                continue
            reply_fragments.append(delta)
            yield {
                "event": "token",
                "data": {"delta": delta},
            }

        reply_text = "".join(reply_fragments).strip()
        if not reply_text:
            reply_text = await self._orchestrator.generate_reply(
                context["history"], language=payload.locale
            )

        assistant_message = await self._append_message(
            context["chat_session"],
            role="assistant",
            content=reply_text,
        )

        history = await self._persist_transcript(context["chat_session"], context["user"].id)
        await self._capture_memory(
            user=context["user"],
            chat_session=context["chat_session"],
            history=history,
        )

        yield {
            "event": "complete",
            "data": {
                "session_id": str(context["chat_session"].id),
                "message": ChatMessage.model_validate(assistant_message).model_dump(),
                "recommended_therapist_ids": context["recommended_ids"],
            },
        }

    async def _get_or_create_user(self, user_id: UUID) -> User:
        user = await self._session.get(User, user_id)
        if user:
            return user

        user = User(id=user_id)
        self._session.add(user)
        await self._session.flush()
        return user

    async def _get_or_create_session(
        self, user: User, session_id: UUID | None
    ) -> ChatSession:
        if session_id:
            existing = await self._session.get(ChatSession, session_id)
            if existing:
                if existing.user_id != user.id:
                    raise ValueError("Session does not belong to requesting user.")
                return existing

        chat_session = ChatSession(user_id=user.id)
        self._session.add(chat_session)
        await self._session.flush()
        return chat_session

    async def _append_message(
        self, chat_session: ChatSession, role: str, content: str
    ) -> ChatMessage:
        next_index = await self._next_sequence_index(chat_session.id)
        record = ChatMessageModel(
            session_id=chat_session.id,
            role=role,
            content=content,
            sequence_index=next_index,
        )
        self._session.add(record)
        await self._session.flush()
        return ChatMessage(
            role=record.role,
            content=record.content,
            created_at=record.created_at,
        )

    async def _prepare_turn(self, payload: ChatRequest) -> dict[str, Any]:
        user = await self._get_or_create_user(payload.user_id)
        chat_session = await self._get_or_create_session(user, payload.session_id)
        await self._append_message(chat_session, role="user", content=payload.message)

        history = await self._load_history(chat_session.id)
        therapist_recs = await self._recommend_therapists(payload.message)
        recommended_ids = [str(therapist.id) for therapist in therapist_recs]

        return {
            "user": user,
            "chat_session": chat_session,
            "history": history,
            "therapist_recs": therapist_recs,
            "recommended_ids": recommended_ids,
        }

    async def _persist_transcript(self, chat_session: ChatSession, user_id: UUID) -> list[dict[str, str]]:
        history = await self._load_history(chat_session.id)
        await self._storage.persist_transcript(
            session_id=chat_session.id,
            user_id=user_id,
            messages=history,
        )
        return history

    async def _load_history(self, session_id: UUID) -> list[dict[str, str]]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.sequence_index.asc())
        )
        result = await self._session.execute(stmt)
        messages = result.scalars().all()
        return [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]

    async def _next_sequence_index(self, session_id: UUID) -> int:
        stmt = (
            select(func.max(ChatMessageModel.sequence_index))
            .where(ChatMessageModel.session_id == session_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        current = result.scalar_one_or_none()
        if current is None:
            return 0
        return current + 1

    async def _recommend_therapists(self, message: str) -> list[Therapist]:
        keywords = {
            "焦虑": "焦虑管理",
            "压力": "认知行为疗法",
            "紧张": "认知行为疗法",
            "失眠": "认知行为疗法",
            "睡": "认知行为疗法",
            "家庭": "家庭治疗",
            "婚姻": "家庭治疗",
            "孩子": "青少年成长",
        }

        lowered = message.lower()
        matched_topics = {topic for key, topic in keywords.items() if key in lowered}

        if not matched_topics:
            return []

        stmt = select(Therapist).limit(10)
        result = await self._session.execute(stmt)
        therapists = [
            therapist
            for therapist in result.scalars().all()
            if matched_topics.intersection(set(therapist.specialties or []))
        ]
        return therapists[:3]

    async def _capture_memory(
        self,
        *,
        user: User,
        chat_session: ChatSession,
        history: list[dict[str, str]],
    ) -> None:
        if not self._memory:
            return

        try:
            await self._memory.capture(
                user=user,
                session=chat_session,
                history=history,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to capture conversation memory: %s", exc, exc_info=exc)
