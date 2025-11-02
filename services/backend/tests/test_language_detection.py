from __future__ import annotations

import pytest

from app.services.language_detection import LanguageDetector


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("我最近压力很大，晚上睡不着。", "zh-CN"),
        ("Thank you for listening to me today.", "en-US"),
        ("感謝你今天的陪伴，讓我放心不少。", "zh-TW"),
        ("", "zh-CN"),
    ],
)
def test_detect_locale(text: str, expected: str) -> None:
    detector = LanguageDetector()
    assert detector.detect_locale(text) == expected


def test_detect_locale_honours_hint_when_ambiguous() -> None:
    detector = LanguageDetector()
    ambiguous = "12345 $$ @@"
    assert detector.detect_locale(ambiguous, hinted_locale="en-US") == "en-US"
    assert detector.detect_locale(ambiguous, hinted_locale="zh-CN") == "zh-CN"
