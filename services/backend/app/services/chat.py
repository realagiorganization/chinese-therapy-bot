from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.models import ChatMessage as ChatMessageModel
from app.models import ChatSession, Therapist, User


class ChatService:
    """Chat orchestration coordinating persistence and recommendation stubs."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_turn(self, payload: ChatRequest) -> ChatResponse:
        user = await self._get_or_create_user(payload.user_id)
        chat_session = await self._get_or_create_session(user, payload.session_id)

        await self._append_message(
            chat_session,
            role="user",
            content=payload.message,
        )

        reply_text = self._generate_placeholder_response(payload.message)
        therapist_recs = await self._recommend_therapists(payload.message)

        assistant_message = await self._append_message(
            chat_session,
            role="assistant",
            content=reply_text,
        )

        return ChatResponse(
            session_id=chat_session.id,
            reply=ChatMessage.model_validate(assistant_message),
            recommended_therapist_ids=[str(therapist.id) for therapist in therapist_recs],
        )

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

    def _generate_placeholder_response(self, message: str) -> str:
        if "焦虑" in message:
            return "我注意到你提到了焦虑。试着进行三分钟的深呼吸练习，并记录触发焦虑的情境。"
        if "睡" in message or "失眠" in message:
            return "保持规律的睡前仪式会有所帮助，比如泡脚或听轻音乐。我们可以一起记录这一周的睡眠状况。"
        if "压力" in message:
            return "当压力累积时，适度的身体活动和碎片化休息很重要。可以尝试番茄钟安排一天的节奏。"
        return "我在这里陪伴你。可以告诉我今天最想分享的事情，我们一起找出可以改善的方向。"
