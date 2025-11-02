from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_asr_service
from app.core.app import create_app
from app.services.asr import AutomaticSpeechRecognitionService


class StubASRService:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict[str, Any]] = []
        self.is_configured = True

    async def transcribe_audio(self, audio: bytes, *, content_type: str, language: str) -> str:
        self.calls.append(
            {
                "audio": audio,
                "content_type": content_type,
                "language": language,
            }
        )
        return self.text


class ErroringASRService(StubASRService):
    async def transcribe_audio(self, audio: bytes, *, content_type: str, language: str) -> str:
        raise ValueError("bad audio")


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_transcribe_returns_service_unavailable_when_unconfigured(client: TestClient) -> None:
    response = client.post(
        "/api/voice/transcribe",
        files={"audio": ("empty.webm", b"\x00\x01", "audio/webm")},
    )
    assert response.status_code == 503
    payload = response.json()
    assert "not configured" in payload["detail"]


def test_transcribe_returns_transcript_when_configured() -> None:
    app = create_app()
    stub = StubASRService("你好世界")

    async def override_get_asr_service() -> AutomaticSpeechRecognitionService:
        return stub  # type: ignore[return-value]

    app.dependency_overrides[get_asr_service] = override_get_asr_service

    with TestClient(app) as client:
        response = client.post(
            "/api/voice/transcribe",
            files={"audio": ("voice.webm", b"\x00\x01", "audio/webm")},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["text"] == "你好世界"
        assert payload["language"] == "zh-CN"
        assert len(stub.calls) == 1

    app.dependency_overrides.clear()


def test_transcribe_propagates_upstream_errors() -> None:
    app = create_app()
    stub = ErroringASRService("should not return")

    async def override_get_asr_service() -> AutomaticSpeechRecognitionService:
        return stub  # type: ignore[return-value]

    app.dependency_overrides[get_asr_service] = override_get_asr_service

    with TestClient(app) as client:
        response = client.post(
            "/api/voice/transcribe",
            files={"audio": ("voice.webm", b"\x00\x01", "audio/webm")},
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["detail"] == "bad audio"

    app.dependency_overrides.clear()
