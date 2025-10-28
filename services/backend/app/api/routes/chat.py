from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter()


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Process a chat turn and stream assistant response.",
)
async def process_chat_turn(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    return await service.process_turn(payload)
