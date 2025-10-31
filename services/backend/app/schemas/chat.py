from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.therapists import TherapistRecommendation


class ChatMessage(BaseModel):
    role: str = Field(..., description="sender role, e.g. user or assistant")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryHighlight(BaseModel):
    summary: str = Field(..., description="Condensed reflection of a recurring focus.")
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords associated with the memory highlight.",
    )


class ChatRequest(BaseModel):
    user_id: UUID = Field(..., description="Identifier of the user engaged in the session.")
    session_id: Optional[UUID] = Field(
        default=None,
        description="Existing session identifier or null for a new session.",
    )
    message: str = Field(..., description="User input text.")
    locale: str = Field(default="zh-CN", description="Preferred localization code.")
    enable_streaming: bool = Field(
        default=True, description="Whether the client expects server-sent token streams."
    )


class ChatResponse(BaseModel):
    session_id: UUID
    reply: ChatMessage
    recommended_therapist_ids: list[str] = Field(
        default_factory=list,
        description="Therapists surfaced during the turn (if any).",
    )
    recommendations: list[TherapistRecommendation] = Field(
        default_factory=list,
        description="Detailed therapist recommendations to surface in the UI.",
    )
    memory_highlights: list[MemoryHighlight] = Field(
        default_factory=list,
        description="Existing conversation memories relevant to this turn.",
    )
