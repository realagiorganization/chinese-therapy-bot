import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter()


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Process a chat turn with optional token streaming.",
)
async def process_chat_turn(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> ChatResponse | StreamingResponse:
    if payload.enable_streaming:
        async def event_stream() -> AsyncIterator[str]:
            try:
                async for event in service.stream_turn(payload):
                    yield _encode_sse(event)
            except ValueError as exc:
                yield _encode_sse({"event": "error", "data": {"detail": str(exc)}})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    try:
        return await service.process_turn(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _encode_sse(event: dict[str, Any]) -> str:
    """Serialize an SSE event payload."""
    event_name = event.get("event")
    data = event.get("data", {})

    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = str(data)

    lines: list[str] = []
    if event_name:
        lines.append(f"event: {event_name}")
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"
