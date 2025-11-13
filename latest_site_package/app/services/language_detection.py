from __future__ import annotations

import math
import re
from typing import Final


class LanguageDetector:
    """Lightweight locale detector tailored for MindWell chat inputs."""

    _CJK_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    _LATIN_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]")
    _CYRILLIC_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F]")
    _CJK_PUNCT_PATTERN: Final[re.Pattern[str]] = re.compile(r"[，。！？、“”『』《》]")
    _TRADITIONAL_MARKERS: Final[set[str]] = {
        "體",
        "臺",
        "灣",
        "愛",
        "學",
        "醫",
        "應",
        "與",
        "們",
        "這",
        "專",
        "課",
        "療",
        "師",
        "讓",
        "謝",
        "點",
        "說",
        "還",
    }

    def __init__(self, *, fallback_locale: str = "zh-CN") -> None:
        self._fallback = fallback_locale

    def detect_locale(self, text: str, *, hinted_locale: str | None = None) -> str:
        """Return the most probable locale for the supplied text."""
        if not text:
            return hinted_locale or self._fallback

        normalized = text.strip()
        if not normalized:
            return hinted_locale or self._fallback

        cjk_matches = self._CJK_PATTERN.findall(normalized)
        latin_matches = self._LATIN_PATTERN.findall(normalized)
        cyrillic_matches = self._CYRILLIC_PATTERN.findall(normalized)
        cjk_punct_matches = self._CJK_PUNCT_PATTERN.findall(normalized)

        cjk_count = len(cjk_matches)
        latin_count = len(latin_matches)
        cyrillic_count = len(cyrillic_matches)
        punctuation_count = len(cjk_punct_matches)
        total_chars = len(normalized)

        if cjk_count > 0 or punctuation_count > 0:
            if self._contains_traditional_marker(normalized):
                return "zh-TW"

            if cjk_count >= 2:
                return "zh-CN"

            density = (cjk_count + punctuation_count) / max(total_chars, 1)
            if density >= 0.15:
                return "zh-CN"

        if cyrillic_count > 0:
            density = cyrillic_count / max(total_chars - punctuation_count, 1)
            if cyrillic_count >= 2 or density >= 0.2:
                return "ru-RU"

        if latin_count > 0:
            density = latin_count / max(total_chars - punctuation_count, 1)
            if latin_count >= 4 or density >= 0.45:
                return "en-US"

        hinted = hinted_locale or ""
        if hinted.lower().startswith("en"):
            if latin_count > 0 and latin_count >= cjk_count:
                return "en-US"
        if hinted.lower().startswith("zh"):
            if cjk_count > 0 or punctuation_count > 0:
                return "zh-CN"
        if hinted.lower().startswith("ru"):
            if cyrillic_count > 0:
                return "ru-RU"

        if latin_count > 0 and cjk_count == 0:
            return "en-US"

        return hinted_locale or self._fallback

    def _contains_traditional_marker(self, text: str) -> bool:
        hits = sum(1 for char in text if char in self._TRADITIONAL_MARKERS)
        if hits == 0:
            return False
        if hits >= 2:
            return True

        cjk_total = len(self._CJK_PATTERN.findall(text)) or 1
        ratio = hits / cjk_total
        return math.isclose(ratio, 0.0) is False and ratio >= 0.1
