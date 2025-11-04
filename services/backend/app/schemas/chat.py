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


class KnowledgeSnippet(BaseModel):
    entry_id: str = Field(..., description="Identifier of the knowledge base article.")
    title: str = Field(..., description="Display title for the snippet.")
    summary: str = Field(
        ...,
        description="Concise overview of why the snippet is relevant.",
    )
    guidance: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions extracted from the knowledge base.",
    )
    source: str | None = Field(
        default=None,
        description="Optional attribution or source label.",
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
    knowledge_snippets: list[KnowledgeSnippet] = Field(
        default_factory=list,
        description="Psychoeducation references or coping strategies related to the turn.",
    )
    resolved_locale: str = Field(
        default="zh-CN",
        description="Locale resolved via automatic language detection for this turn.",
    )
