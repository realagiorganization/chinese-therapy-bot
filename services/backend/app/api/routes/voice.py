from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_asr_service
from app.schemas.voice import TranscriptionResponse
from app.services.asr import AutomaticSpeechRecognitionService

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe uploaded audio using the configured ASR provider.",
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = "zh-CN",
    service: AutomaticSpeechRecognitionService = Depends(get_asr_service),
) -> TranscriptionResponse:
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server speech recognition is not configured.",
        )

    payload = await audio.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio payload is empty.",
        )

    try:
        text = await service.transcribe_audio(
            payload,
            content_type=audio.content_type or "audio/webm",
            language=language,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speech recognition completed without a transcript.",
        )

    return TranscriptionResponse(text=text, language=language)
