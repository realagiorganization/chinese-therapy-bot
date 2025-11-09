from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_chat_service
from app.core.app import create_app


class StreamingStubChatService:
    def __init__(self) -> None:
        self.calls = 0
        self.last_payload = None

    async def process_turn(self, payload):  # pragma: no cover - not used in streaming tests
        raise AssertionError("process_turn should not be invoked for streaming route")

    async def stream_turn(self, payload):
        self.calls += 1
        self.last_payload = payload
        yield {
            "event": "session_established",
            "data": {"session_id": "abc123", "locale": "zh-CN"},
        }
        yield {"event": "token", "data": {"delta": "你好"}}
        yield {
            "event": "complete",
            "data": {
                "session_id": "abc123",
                "message": {
                    "role": "assistant",
                    "content": "你好",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                "resolved_locale": "zh-CN",
                "recommended_therapist_ids": [],
                "recommendations": [],
                "memory_highlights": [],
            },
        }


class ErroringStubChatService(StreamingStubChatService):
    async def stream_turn(self, payload):
        raise ValueError("streaming disabled for this tenant")
        yield  # pragma: no cover - satisfy async generator signature


@contextmanager
def _client_with_service(service):
    app = create_app()

    async def override_get_chat_service():
        return service

    app.dependency_overrides[get_chat_service] = override_get_chat_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _default_payload() -> dict[str, str | None]:
    return {
        "user_id": str(uuid4()),
        "session_id": None,
        "message": "感觉最近工作压力特别大。",
        "locale": "zh-CN",
        "enable_streaming": False,
    }


def test_chat_stream_route_returns_sse_headers_and_events() -> None:
    service = StreamingStubChatService()
    with _client_with_service(service) as client:
        response = client.post(
            "/api/chat/stream",
            json=_default_payload(),
            headers={"Accept": "text/event-stream"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: session_established" in body
    assert "event: token" in body
    assert "event: complete" in body
    assert service.calls == 1
    assert service.last_payload is not None
    assert service.last_payload.enable_streaming is True  # type: ignore[attr-defined]


def test_legacy_therapy_stream_route_aliases_chat_stream() -> None:
    service = StreamingStubChatService()
    with _client_with_service(service) as client:
        response = client.post(
            "/therapy/chat/stream",
            json=_default_payload(),
            headers={"Accept": "text/event-stream"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: complete" in response.text
    assert service.calls == 1
    assert service.last_payload is not None
    assert service.last_payload.enable_streaming is True  # type: ignore[attr-defined]


def test_chat_stream_route_surfaces_error_events() -> None:
    service = ErroringStubChatService()
    with _client_with_service(service) as client:
        response = client.post(
            "/api/chat/stream",
            json=_default_payload(),
            headers={"Accept": "text/event-stream"},
        )
    assert response.status_code == 200
    body = response.text
    assert "event: error" in body
    assert "streaming disabled for this tenant" in body
