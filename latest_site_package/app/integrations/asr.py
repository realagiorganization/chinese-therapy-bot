from __future__ import annotations

from typing import Any

import httpx

from app.core.config import AppSettings


class AzureSpeechTranscriptionError(RuntimeError):
    """Raised when Azure Speech transcription fails."""


class AzureSpeechTranscriber:
    """Thin wrapper around the Azure Speech REST API for short-form transcription."""

    def __init__(self, settings: AppSettings) -> None:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise ValueError("Azure Speech credentials are not configured.")

        self._subscription_key = settings.azure_speech_key.get_secret_value()
        self._region = settings.azure_speech_region
        default_endpoint = (
            f"https://{self._region}.stt.speech.microsoft.com"
            "/speech/recognition/conversation/cognitiveservices/v1"
        )
        endpoint = settings.azure_speech_endpoint or default_endpoint
        self._endpoint = endpoint.rstrip("/")
        self._timeout = httpx.Timeout(30.0)

    async def transcribe(
        self,
        audio: bytes,
        content_type: str,
        *,
        language: str = "zh-CN",
        profanity: str = "Masked",
    ) -> str:
        """Send audio bytes to Azure Speech and return the display text."""
        if not audio:
            raise ValueError("Audio payload is empty.")

        headers = {
            "Ocp-Apim-Subscription-Key": self._subscription_key,
            "Content-Type": content_type or "audio/webm",
            "Accept": "application/json;text/xml",
        }
        params = {
            "language": language or "zh-CN",
            "profanity": profanity,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._endpoint,
                params=params,
                headers=headers,
                content=audio,
            )

        if response.status_code == 401 or response.status_code == 403:
            raise AzureSpeechTranscriptionError("Azure Speech authentication failed.")
        if response.status_code == 429:
            raise AzureSpeechTranscriptionError("Azure Speech request throttled.")
        if response.status_code >= 500:
            raise AzureSpeechTranscriptionError(
                "Azure Speech service is unavailable. Try again later."
            )
        if response.status_code != 200:
            message = _extract_error_message(response)
            raise AzureSpeechTranscriptionError(
                message or f"Azure Speech request failed with status {response.status_code}."
            )

        payload = response.json()
        status = payload.get("RecognitionStatus")
        if status != "Success":
            message = payload.get("DisplayText") or payload.get("Message")
            detail = message or status or "Unknown error"
            raise AzureSpeechTranscriptionError(f"Azure Speech recognition failed: {detail}.")

        text = payload.get("DisplayText") or payload.get("Text") or ""
        return text.strip()


def _extract_error_message(response: httpx.Response) -> str | None:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        message = payload.get("error") or payload.get("Message")
        if isinstance(message, dict):
            detail = message.get("message") or message.get("code")
            return str(detail) if detail else None
        if message:
            return str(message)
    return None
