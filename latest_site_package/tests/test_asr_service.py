import pytest

from app.services.asr import AutomaticSpeechRecognitionService


class DummyTranscriber:
    async def transcribe(self, audio: bytes, content_type: str, *, language: str) -> str:
        assert audio == b"\x00\x01"
        assert content_type == "audio/webm"
        assert language == "zh-CN"
        return "transcribed text"


class FailingTranscriber:
    async def transcribe(self, audio: bytes, content_type: str, *, language: str) -> str:
        raise RuntimeError("Upstream failure")


@pytest.mark.asyncio
async def test_transcribe_audio_returns_text() -> None:
    service = AutomaticSpeechRecognitionService(DummyTranscriber())  # type: ignore[arg-type]
    transcript = await service.transcribe_audio(b"\x00\x01", content_type="audio/webm", language="zh-CN")
    assert transcript == "transcribed text"


@pytest.mark.asyncio
async def test_transcribe_audio_raises_when_not_configured() -> None:
    service = AutomaticSpeechRecognitionService(None)
    with pytest.raises(RuntimeError):
        await service.transcribe_audio(b"\x01", content_type="audio/webm", language="zh-CN")


@pytest.mark.asyncio
async def test_transcribe_audio_raises_on_upstream_error() -> None:
    service = AutomaticSpeechRecognitionService(FailingTranscriber())  # type: ignore[arg-type]
    with pytest.raises(ValueError) as exc:
        await service.transcribe_audio(b"\x00\x01", content_type="audio/webm", language="zh-CN")
    assert "Upstream failure" in str(exc.value)


@pytest.mark.asyncio
async def test_transcribe_audio_rejects_empty_payload() -> None:
    service = AutomaticSpeechRecognitionService(DummyTranscriber())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await service.transcribe_audio(b"", content_type="audio/webm", language="zh-CN")
