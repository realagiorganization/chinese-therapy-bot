from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_memory_service
from app.schemas.memory import ConversationMemoryItem, ConversationMemoryListResponse
from app.services.memory import ConversationMemoryService


router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=ConversationMemoryListResponse,
    summary="List conversation memories captured for a user.",
)
async def list_conversation_memories(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    service: ConversationMemoryService = Depends(get_memory_service),
) -> ConversationMemoryListResponse:
    try:
        records = await service.list_memories(user_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    items = [ConversationMemoryItem.model_validate(record) for record in records]
    return ConversationMemoryListResponse(items=items)
