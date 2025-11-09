from __future__ import annotations

from app.integrations.asr import AzureSpeechTranscriber, AzureSpeechTranscriptionError


class AutomaticSpeechRecognitionService:
    """Coordinate server-side speech transcription."""

    def __init__(self, transcriber: AzureSpeechTranscriber | None) -> None:
        self._transcriber = transcriber

    @property
    def is_configured(self) -> bool:
        return self._transcriber is not None

    async def transcribe_audio(
        self,
        audio: bytes,
        *,
        content_type: str,
        language: str,
    ) -> str:
        if not audio:
            raise ValueError("Audio payload is empty.")
        if not self._transcriber:
            raise RuntimeError("Server speech recognition is not configured.")

        try:
            transcript = await self._transcriber.transcribe(
                audio,
                content_type or "audio/webm",
                language=language,
            )
        except AzureSpeechTranscriptionError as exc:
            raise ValueError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive catch-all
            raise ValueError(str(exc)) from exc
        return transcript
