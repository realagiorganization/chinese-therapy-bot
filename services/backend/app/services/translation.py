from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Sequence

from app.integrations.llm import ChatOrchestrator
from app.schemas.therapists import TherapistImportRecord, TherapistLocalePayload
from app.services.language_detection import LanguageDetector

logger = logging.getLogger(__name__)

_BASIC_TERM_TRANSLATIONS: dict[str, dict[str, str]] = {
    "注册心理咨询师": {
        "en-us": "Licensed Psychological Counselor",
        "ru-ru": "Сертифицированный психолог-консультант",
        "zh-tw": "註冊心理諮商師",
    },
    "国家二级心理咨询师": {
        "en-us": "National Level-2 Psychological Counselor",
        "ru-ru": "Психолог-консультант II категории",
        "zh-tw": "國家二級心理諮商師",
    },
    "认知行为疗法": {
        "en-us": "Cognitive Behavioral Therapy",
        "ru-ru": "Когнитивно-поведенческая терапия",
        "zh-tw": "認知行為療法",
    },
    "焦虑管理": {
        "en-us": "Anxiety Management",
        "ru-ru": "Управление тревогой",
        "zh-tw": "焦慮調節",
    },
    "家庭治疗": {
        "en-us": "Family Therapy",
        "ru-ru": "Семейная терапия",
        "zh-tw": "家庭治療",
    },
    "青少年成长": {
        "en-us": "Adolescent Development",
        "ru-ru": "Подростковое развитие",
        "zh-tw": "青少年成長",
    },
    "拥有 8 年临床经验，擅长职场压力与情绪调节。": {
        "en-us": "Eight years of clinical experience supporting workplace stress and emotional regulation.",
        "ru-ru": "8 лет клинического опыта в поддержке управления рабочим стрессом и эмоциями.",
        "zh-tw": "擁有 8 年臨床經驗，擅長職場壓力與情緒調節。",
    },
    "关注家庭关系修复，结合正念减压技巧。": {
        "en-us": "Focuses on repairing family relationships and blends mindfulness-based stress relief.",
        "ru-ru": "Сфокусирована на восстановлении семейных отношений и сочетает майндфулнес для снижения стресса.",
        "zh-tw": "關注家庭關係修復，結合正念減壓技巧。",
    },
}


class TranslationService:
    """Utility providing lightweight locale detection and text translation helpers."""

    _DEFAULT_TARGET_LOCALES: tuple[str, ...] = ("zh-CN", "zh-TW", "en-US", "ru-RU")

    def __init__(
        self,
        orchestrator: ChatOrchestrator | None = None,
        *,
        detector: LanguageDetector | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._detector = detector or LanguageDetector()
        self._cache: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    @property
    def default_locales(self) -> tuple[str, ...]:
        return self._DEFAULT_TARGET_LOCALES

    def detect_locale(self, text: str, *, fallback: str = "zh-CN") -> str:
        if not text:
            return fallback
        return self._detector.detect_locale(text, hinted_locale=fallback)

    def are_locales_equivalent(self, first: str | None, second: str | None) -> bool:
        if not first or not second:
            return False
        return self._normalize_locale(first) == self._normalize_locale(second)

    async def translate_text(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None = None,
    ) -> str:
        if not text:
            return ""

        normalized_target = self._normalize_locale(target_locale)
        normalized_source = self._normalize_locale(source_locale) if source_locale else None
        if normalized_source and normalized_source == normalized_target:
            return text

        cache_key = (text, normalized_target)
        async with self._lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        translated = await self._perform_translation(
            text,
            target_locale=normalized_target,
            source_locale=normalized_source,
        )

        async with self._lock:
            self._cache[cache_key] = translated
        return translated

    async def translate_list(
        self,
        values: Iterable[str],
        *,
        target_locale: str,
        source_locale: str | None = None,
    ) -> list[str]:
        translated: list[str] = []
        cache: dict[str, str] = {}
        for value in values:
            text = value.strip() if isinstance(value, str) else str(value)
            if not text:
                translated.append(text)
                continue
            if text not in cache:
                cache[text] = await self.translate_text(
                    text,
                    target_locale=target_locale,
                    source_locale=source_locale,
                )
            translated.append(cache[text])
        return translated

    async def ensure_therapist_localizations(
        self,
        records: Sequence[TherapistImportRecord],
        *,
        target_locales: Sequence[str],
    ) -> list[TherapistImportRecord]:
        enriched: list[TherapistImportRecord] = []
        for record in records:
            enriched.append(
                await self._enrich_record_localizations(record, target_locales=target_locales)
            )
        return enriched

    async def _enrich_record_localizations(
        self,
        record: TherapistImportRecord,
        *,
        target_locales: Sequence[str],
    ) -> TherapistImportRecord:
        if not target_locales:
            return record

        locale_map: dict[str, TherapistLocalePayload] = {}
        for localization in record.localizations:
            normalized = self._normalize_locale(localization.locale)
            if not normalized:
                continue
            locale_map[normalized] = localization

        inferred_source = self._infer_record_locale(record, locale_map.values())

        for target in target_locales:
            normalized_target = self._normalize_locale(target)
            if normalized_target in locale_map:
                continue

            translated_title = await self.translate_text(
                record.title or record.name,
                target_locale=target,
                source_locale=inferred_source,
            )
            translated_biography = await self.translate_text(
                record.biography or "",
                target_locale=target,
                source_locale=inferred_source,
            )
            locale_map[normalized_target] = TherapistLocalePayload(
                locale=target,
                title=translated_title,
                biography=translated_biography,
            )

        ordered = [locale_map[key] for key in sorted(locale_map)]
        record.localizations = ordered
        return record

    async def _perform_translation(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None,
    ) -> str:
        if not self._orchestrator:
            return self._heuristic_translation(
                text,
                target_locale=target_locale,
                source_locale=source_locale,
            )

        try:
            return await self._orchestrator.translate_text(
                text,
                target_locale=target_locale,
                source_locale=source_locale,
            )
        except Exception as exc:  # pragma: no cover - network or provider failure
            logger.warning(
                "LLM translation failed; falling back to heuristics (target=%s): %s",
                target_locale,
                exc,
            )
            return self._heuristic_translation(
                text,
                target_locale=target_locale,
                source_locale=source_locale,
            )

    def _infer_record_locale(
        self,
        record: TherapistImportRecord,
        localizations: Iterable[TherapistLocalePayload],
    ) -> str:
        preferred: str | None = None
        for localization in localizations:
            normalized = self._normalize_locale(localization.locale)
            if normalized.startswith("zh"):
                return normalization
            preferred = preferred or normalized

        probe_fields = [
            record.title,
            record.biography,
            record.name,
        ]
        for field in probe_fields:
            if field:
                detected = self.detect_locale(field, fallback="zh-CN")
                if detected:
                    return self._normalize_locale(detected)
        return preferred or "zh-cn"

    def _heuristic_translation(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None,
    ) -> str:
        normalized_target = self._normalize_locale(target_locale)
        normalized_source = self._normalize_locale(source_locale) if source_locale else None

        if normalized_source and normalized_source == normalized_target:
            return text

        # Simplified Chinese -> Traditional Chinese fallback for key characters.
        if normalized_source == "zh-cn" and normalized_target == "zh-tw":
            return (
                text.replace("疗", "療")
                .replace("虑", "慮")
                .replace("复", "復")
                .replace("国", "國")
                .replace("专", "專")
                .replace("级", "級")
                .replace("术", "術")
            )

        # Traditional -> Simplified basic mapping.
        if normalized_source == "zh-tw" and normalized_target == "zh-cn":
            return (
                text.replace("療", "疗")
                .replace("慮", "虑")
                .replace("復", "复")
                .replace("國", "国")
                .replace("專", "专")
                .replace("級", "级")
                .replace("術", "术")
            )

        replacements_applied = False
        translated = text
        for phrase, translations in _BASIC_TERM_TRANSLATIONS.items():
            replacement = translations.get(normalized_target)
            if replacement and phrase in translated:
                translated = translated.replace(phrase, replacement)
                replacements_applied = True
        if replacements_applied:
            return translated

        # For unsupported locales fall back to source text.
        return text

    def _normalize_locale(self, value: str | None) -> str:
        if not value:
            return ""
        return value.replace("_", "-").lower()
