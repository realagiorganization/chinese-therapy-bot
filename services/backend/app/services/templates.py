from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable, Sequence


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatTemplate:
    """Localized prompt template for common mental health scenes."""

    id: str
    topic: str
    locale: str
    title: str
    user_prompt: str
    assistant_example: str
    follow_up_questions: tuple[str, ...]
    self_care_tips: tuple[str, ...]
    keywords: tuple[str, ...]
    tags: tuple[str, ...]
    priority: int


class ChatTemplateService:
    """Load and filter curated chat templates for quick-start scenarios."""

    _DATASET_FILENAME = "chat_templates.json"

    def __init__(self, *, templates: Sequence[ChatTemplate] | None = None) -> None:
        self._templates: tuple[ChatTemplate, ...] = (
            tuple(templates) if templates else self._load_templates()
        )

    def list_templates(
        self,
        *,
        locale: str,
        topic: str | None = None,
        keywords: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[ChatTemplate]:
        """Return templates filtered by locale, topic, and optional keywords."""
        keyword_filter = {
            keyword.lower()
            for keyword in keywords or ()
            if isinstance(keyword, str) and keyword.strip()
        }
        topic_filter = (topic or "").strip().lower()

        results: list[ChatTemplate] = []
        seen_ids: set[str] = set()

        for candidate_locale in self._locale_candidates(locale):
            matching = [
                template
                for template in self._templates
                if template.locale == candidate_locale
            ]
            if topic_filter:
                matching = [
                    template
                    for template in matching
                    if template.topic == topic_filter
                    or topic_filter in template.tags
                    or topic_filter in (kw.lower() for kw in template.keywords)
                ]
            if keyword_filter:
                matching = [
                    template
                    for template in matching
                    if keyword_filter.intersection(
                        {kw.lower() for kw in template.keywords}
                    )
                ]

            for template in matching:
                if template.id in seen_ids:
                    continue
                results.append(template)
                seen_ids.add(template.id)
                if limit and len(results) >= limit:
                    return results[:limit]

        if limit:
            return results[:limit]
        return results

    def topics(self, *, locale: str) -> list[str]:
        """Return the ordered set of topics available for a locale."""
        ordered: list[str] = []
        seen: set[str] = set()
        for candidate_locale in self._locale_candidates(locale):
            for template in self._templates:
                if template.locale != candidate_locale:
                    continue
                if template.topic in seen:
                    continue
                ordered.append(template.topic)
                seen.add(template.topic)
        return ordered

    def _locale_candidates(self, locale: str | None) -> list[str]:
        normalized = self._normalize_locale(locale)
        language = normalized.split("-", 1)[0]

        candidates: list[str] = [normalized]
        if language == "zh":
            if normalized != "zh-CN":
                candidates.append("zh-CN")
            candidates.append("en-US")
        elif language == "en":
            if normalized != "en-US":
                candidates.append("en-US")
            candidates.append("zh-CN")
        else:
            candidates.extend(["en-US", "zh-CN"])

        # Preserve order while removing duplicates.
        seen: set[str] = set()
        unique_candidates: list[str] = []
        for candidate in candidates:
            if candidate not in seen:
                unique_candidates.append(candidate)
                seen.add(candidate)
        return unique_candidates

    def _normalize_locale(self, locale: str | None) -> str:
        if not locale:
            return "zh-CN"

        parts = str(locale).replace("_", "-").split("-")
        language = parts[0].lower()
        region = parts[1].upper() if len(parts) > 1 else None

        if language == "zh":
            return f"zh-{region or 'CN'}"
        if language == "en":
            return f"en-{region or 'US'}"
        if language == "ru":
            return f"ru-{region or 'RU'}"
        if region:
            return f"{language}-{region}"
        return f"{language}-US"

    def resolve_locale(self, locale: str | None) -> str:
        """Expose locale normalization for API consumers."""
        return self._normalize_locale(locale)

    def _load_templates(self) -> tuple[ChatTemplate, ...]:
        raw_text = None
        last_error: Exception | None = None
        try:
            dataset_path = resources.files("app.data").joinpath(self._DATASET_FILENAME)
            raw_text = dataset_path.read_text(encoding="utf-8")
        except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover
            logger.error("Template dataset is unavailable: %s", exc)
        except OSError as exc:
            last_error = exc
            logger.error("Failed to read template dataset: %s", exc)

        if raw_text is None:
            fallback_path = Path(__file__).resolve().parent.parent / "data" / self._DATASET_FILENAME
            try:
                raw_text = fallback_path.read_text(encoding="utf-8")
            except OSError as exc:
                last_error = exc
                logger.error("Failed to read template dataset fallback: %s", exc)
                return tuple()

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guardrail
            logger.error("Template dataset contains invalid JSON: %s", exc)
            return tuple()

        templates: list[ChatTemplate] = []
        for entry in payload or []:
            base = entry if isinstance(entry, dict) else {}
            template_id = str(base.get("id") or "").strip()
            topic = str(base.get("topic") or "").strip().lower()
            priority = int(base.get("priority") or 0)
            keywords = tuple(
                str(keyword).strip()
                for keyword in base.get("keywords", [])
                if str(keyword).strip()
            )
            tags = tuple(
                str(tag).strip().lower()
                for tag in base.get("tags", [])
                if str(tag).strip()
            )

            localized_map = base.get("locales", {})
            if not template_id or not topic or not localized_map:
                continue

            for locale, localized_data in localized_map.items():
                details = localized_data if isinstance(localized_data, dict) else {}
                title = str(details.get("title") or "").strip()
                user_prompt = str(details.get("user_prompt") or "").strip()
                assistant_example = str(details.get("assistant_example") or "").strip()
                follow_up_questions = tuple(
                    str(question).strip()
                    for question in details.get("follow_up_questions", [])
                    if str(question).strip()
                )
                self_care_tips = tuple(
                    str(tip).strip()
                    for tip in details.get("self_care_tips", [])
                    if str(tip).strip()
                )

                if not title or not user_prompt:
                    continue

                templates.append(
                    ChatTemplate(
                        id=template_id,
                        topic=topic,
                        locale=self._normalize_locale(locale),
                        title=title,
                        user_prompt=user_prompt,
                        assistant_example=assistant_example,
                        follow_up_questions=follow_up_questions,
                        self_care_tips=self_care_tips,
                        keywords=keywords,
                        tags=tags,
                        priority=priority,
                    )
                )

        templates.sort(
            key=lambda template: (-template.priority, template.topic, template.title)
        )
        return tuple(templates)


def load_templates_from_dataset() -> tuple[ChatTemplate, ...]:
    """Helper for tests to load the compiled dataset."""
    return ChatTemplateService()._templates
