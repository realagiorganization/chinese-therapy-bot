from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Response payload for server-side audio transcription."""

    text: str = Field(..., description="Recognized transcript for the uploaded audio.")
    language: str = Field(..., description="BCP-47 language tag used during recognition.")
