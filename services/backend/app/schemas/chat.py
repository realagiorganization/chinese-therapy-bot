from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="sender role, e.g. user or assistant")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None, description="Existing session identifier or null for new session."
    )
    message: str = Field(..., description="User input text.")
    locale: str = Field(default="zh-CN", description="Preferred localization code.")
    enable_streaming: bool = Field(
        default=True, description="Whether the client expects server-sent token streams."
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: ChatMessage
    recommended_therapist_ids: list[str] = Field(
        default_factory=list,
        description="Therapists surfaced during the turn (if any).",
    )
