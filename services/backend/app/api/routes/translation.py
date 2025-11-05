from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_translation_service
from app.schemas.translation import TranslationBatchRequest, TranslationBatchResponse
from app.services.translation import TranslationService

router = APIRouter()


@router.post(
    "/batch",
    response_model=TranslationBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate a batch of UI strings into the requested locale.",
)
async def translate_batch(
    payload: TranslationBatchRequest,
    translator: TranslationService = Depends(get_translation_service),
) -> TranslationBatchResponse:
    """Return translated strings keyed by the provided identifiers."""
    source_locale = payload.source_locale or "en-US"
    if translator.are_locales_equivalent(payload.target_locale, source_locale):
        passthrough = {entry.key: entry.text for entry in payload.entries}
        return TranslationBatchResponse(
            target_locale=payload.target_locale,
            source_locale=source_locale,
            translations=passthrough,
        )

    translations: dict[str, str] = {}
    for entry in payload.entries:
        translated = await translator.translate_text(
            entry.text,
            target_locale=payload.target_locale,
            source_locale=source_locale,
        )
        translations[entry.key] = translated

    return TranslationBatchResponse(
        target_locale=payload.target_locale,
        source_locale=source_locale,
        translations=translations,
    )
