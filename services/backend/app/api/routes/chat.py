import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service, get_chat_template_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.templates import ChatTemplateItem, ChatTemplateListResponse
from app.services.chat import ChatService, TokenQuotaExceeded
from app.services.templates import ChatTemplateService

router = APIRouter()
legacy_router = APIRouter(prefix="/therapy", tags=["legacy"])


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Process a chat turn with optional token streaming.",
)
async def process_chat_turn(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> ChatResponse | StreamingResponse:
    if payload.enable_streaming:
        return _stream_chat_response(payload, service)

    try:
        return await service.process_turn(payload)
    except TokenQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/stream",
    summary="Stream chat responses via server-sent events.",
    response_class=StreamingResponse,
    include_in_schema=False,
)
async def stream_chat_turn(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> StreamingResponse:
    payload.enable_streaming = True
    return _stream_chat_response(payload, service)


@legacy_router.post(
    "/chat/stream",
    summary="Legacy streaming endpoint (use /api/chat/message).",
    response_class=StreamingResponse,
    include_in_schema=False,
    deprecated=True,
)
async def legacy_stream_chat_turn(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> StreamingResponse:
    payload.enable_streaming = True
    return _stream_chat_response(payload, service)


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


@router.get(
    "/templates",
    response_model=ChatTemplateListResponse,
    summary="List curated chat templates for quick-start scenes.",
)
async def list_chat_templates(
    locale: str = Query("zh-CN", description="Desired locale, e.g. zh-CN or en-US."),
    topic: str | None = Query(
        default=None, description="Optional topic filter such as anxiety or sleep."
    ),
    keywords: list[str] = Query(
        default_factory=list,
        description="Optional keyword filters applied to template keywords.",
    ),
    limit: int = Query(
        5,
        ge=1,
        le=20,
        description="Maximum number of templates to return.",
    ),
    service: ChatTemplateService = Depends(get_chat_template_service),
) -> ChatTemplateListResponse:
    templates = service.list_templates(
        locale=locale,
        topic=topic,
        keywords=keywords,
        limit=limit,
    )
    return ChatTemplateListResponse(
        locale=service.resolve_locale(locale),
        topics=service.topics(locale=locale),
        templates=[ChatTemplateItem.from_domain(template) for template in templates],
    )


def _stream_chat_response(payload: ChatRequest, service: ChatService) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in service.stream_turn(payload):
                yield _encode_sse(event)
        except TokenQuotaExceeded as exc:
            yield _encode_sse(
                {
                    "event": "error",
                    "data": {"detail": str(exc), "code": "chat_tokens_exhausted"},
                }
            )
        except ValueError as exc:
            yield _encode_sse({"event": "error", "data": {"detail": str(exc)}})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
