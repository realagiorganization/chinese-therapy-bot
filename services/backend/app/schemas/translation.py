from __future__ import annotations

from pydantic import BaseModel, Field


class TranslationEntry(BaseModel):
    key: str = Field(..., description="Stable identifier for the text entry.")
    text: str = Field("", description="Source text in the base locale.")


class TranslationBatchRequest(BaseModel):
    target_locale: str = Field(..., description="Locale code to translate into.")
    source_locale: str | None = Field(
        default="en-US",
        description="Locale code of the provided source text. Defaults to en-US.",
    )
    namespace: str | None = Field(
        default=None,
        description="Optional namespace identifier for grouping translations.",
    )
    entries: list[TranslationEntry] = Field(
        default_factory=list,
        description="Collection of key-text pairs to translate.",
    )


class TranslationBatchResponse(BaseModel):
    target_locale: str = Field(..., description="Locale code translations were generated for.")
    source_locale: str = Field(..., description="Locale code translations were sourced from.")
    translations: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of entry keys to translated text.",
    )
