from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable, Sequence

from app.integrations.embeddings import EmbeddingClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KnowledgeBaseEntry:
    """Single knowledge base article used to enrich chat prompts."""

    entry_id: str
    locale: str
    title: str
    summary: str
    guidance: tuple[str, ...]
    keywords: tuple[str, ...]
    tags: tuple[str, ...]
    source: str | None = None


class KnowledgeBaseService:
    """Retrieve psychoeducation snippets to ground LLM responses."""

    _DATASET_FILENAME = "knowledge_base.json"

    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._entries: tuple[KnowledgeBaseEntry, ...] = self._load_entries()
        self._embedding_cache: dict[str, list[float]] = {}
        self._embedding_lock = asyncio.Lock()

    async def search(
        self,
        query: str,
        *,
        locale: str,
        limit: int = 3,
    ) -> list[KnowledgeBaseEntry]:
        """Return the most relevant knowledge base entries for a prompt."""
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        candidates = self._entries_for_locale(locale)
        if not candidates:
            return []

        scored = await self._score_with_embeddings(normalized_query, candidates)
        if not scored:
            scored = self._score_with_keywords(normalized_query, candidates)

        scored.sort(key=lambda item: item[0], reverse=True)
        unique: list[KnowledgeBaseEntry] = []
        seen: set[str] = set()
        for score, entry in scored:
            if score <= 0:
                continue
            if entry.entry_id in seen:
                continue
            unique.append(entry)
            seen.add(entry.entry_id)
            if limit and len(unique) >= limit:
                break
        return unique

    def _entries_for_locale(self, locale: str) -> list[KnowledgeBaseEntry]:
        candidates: list[str] = self._locale_candidates(locale)
        results: list[KnowledgeBaseEntry] = []
        seen: set[str] = set()
        for candidate in candidates:
            for entry in self._entries:
                if entry.locale != candidate:
                    continue
                if entry.entry_id in seen:
                    continue
                results.append(entry)
                seen.add(entry.entry_id)
        return results

    async def _score_with_embeddings(
        self,
        query: str,
        entries: Sequence[KnowledgeBaseEntry],
    ) -> list[tuple[float, KnowledgeBaseEntry]]:
        if not self._embedding_client:
            return []

        async with self._embedding_lock:
            missing = [entry for entry in entries if entry.entry_id not in self._embedding_cache]
            if missing:
                documents = [self._entry_document(entry) for entry in missing]
                vectors = await self._embedding_client.embed_texts(documents)
                for entry, vector in zip(missing, vectors):
                    if vector:
                        self._embedding_cache[entry.entry_id] = vector

        query_vector = await self._embedding_client.embed_query(query)
        scored: list[tuple[float, KnowledgeBaseEntry]] = []
        for entry in entries:
            vector = self._embedding_cache.get(entry.entry_id)
            if not vector:
                continue
            score = self._embedding_client.cosine_similarity(query_vector, vector)
            if score > 0:
                scored.append((score, entry))
        return scored

    def _score_with_keywords(
        self,
        query: str,
        entries: Sequence[KnowledgeBaseEntry],
    ) -> list[tuple[float, KnowledgeBaseEntry]]:
        lowered = query.lower()
        scored: list[tuple[float, KnowledgeBaseEntry]] = []
        for entry in entries:
            score = 0.0
            for keyword in entry.keywords:
                token = keyword.lower()
                if token and token in lowered:
                    score += 0.2
            for tag in entry.tags:
                token = tag.lower()
                if token and token in lowered:
                    score += 0.1
            if score > 0:
                scored.append((min(score, 1.0), entry))
        return scored

    def _entry_document(self, entry: KnowledgeBaseEntry) -> str:
        segments: list[str] = [
            entry.title,
            entry.summary,
            " ".join(entry.guidance),
            " ".join(entry.keywords),
            " ".join(entry.tags),
        ]
        if entry.source:
            segments.append(entry.source)
        return " ".join(segment.strip() for segment in segments if segment).strip()

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

        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate not in seen:
                unique.append(candidate)
                seen.add(candidate)
        return unique

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

    def _load_entries(self) -> tuple[KnowledgeBaseEntry, ...]:
        raw_text = self._read_dataset()
        if raw_text is None:
            logger.error("Knowledge base dataset could not be loaded; returning empty set.")
            return tuple()

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guardrail
            logger.error("Knowledge base dataset contains invalid JSON: %s", exc)
            return tuple()

        entries: list[KnowledgeBaseEntry] = []
        for item in payload or []:
            if not isinstance(item, dict):
                continue
            entry_id = str(item.get("id") or "").strip()
            locale = str(item.get("locale") or "zh-CN").strip() or "zh-CN"
            title = str(item.get("title") or "").strip()
            summary = str(item.get("summary") or "").strip()
            guidance = tuple(
                str(line).strip()
                for line in item.get("guidance", [])
                if isinstance(line, str) and line.strip()
            )
            keywords = tuple(
                str(keyword).strip()
                for keyword in item.get("keywords", [])
                if isinstance(keyword, str) and keyword.strip()
            )
            tags = tuple(
                str(tag).strip()
                for tag in item.get("tags", [])
                if isinstance(tag, str) and tag.strip()
            )
            source = str(item.get("source") or "").strip() or None

            if not entry_id or not title or not summary:
                continue

            entries.append(
                KnowledgeBaseEntry(
                    entry_id=entry_id,
                    locale=self._normalize_locale(locale),
                    title=title,
                    summary=summary,
                    guidance=guidance,
                    keywords=keywords,
                    tags=tags,
                    source=source,
                )
            )
        return tuple(entries)

    def _read_dataset(self) -> str | None:
        try:
            dataset_path = resources.files("app.data").joinpath(self._DATASET_FILENAME)
            return dataset_path.read_text(encoding="utf-8")
        except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover
            logger.debug("Knowledge base dataset not packaged: %s", exc)
        except OSError as exc:
            logger.warning("Failed to read packaged knowledge base dataset: %s", exc)

        fallback_path = Path(__file__).resolve().parent.parent / "data" / self._DATASET_FILENAME
        try:
            return fallback_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to read knowledge base dataset fallback: %s", exc)
        return None


class NullKnowledgeBaseService(KnowledgeBaseService):
    """Fallback knowledge base service that never returns results."""

    def __init__(self) -> None:
        super().__init__(embedding_client=None)

    async def search(
        self,
        query: str,
        *,
        locale: str,
        limit: int = 3,
    ) -> list[KnowledgeBaseEntry]:
        return []
