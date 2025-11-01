from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ConversationMemoryItem(BaseModel):
    """Serialized representation of a stored conversation memory."""

    memory_id: str = Field(validation_alias="id")
    user_id: str
    session_id: str | None = None
    keywords: List[str] = Field(default_factory=list)
    summary: str
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationMemoryListResponse(BaseModel):
    """Envelope returned when listing stored memories for a user."""

    items: list[ConversationMemoryItem]
