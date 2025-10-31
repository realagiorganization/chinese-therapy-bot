from __future__ import annotations

import hashlib
import logging
import math
from typing import Iterable, Sequence

from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.core.config import AppSettings


logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Unified interface for embedding text with Azure OpenAI, OpenAI, or local heuristics."""

    _FALLBACK_DIMENSIONS = 64

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._azure_client: AsyncAzureOpenAI | None = None
        self._azure_model: str | None = None
        self._openai_client: AsyncOpenAI | None = None
        self._openai_model: str = settings.openai_embedding_model or "text-embedding-3-small"

        if (
            settings.azure_openai_api_key
            and settings.azure_openai_endpoint
            and settings.azure_openai_embeddings_deployment
        ):
            self._azure_client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key.get_secret_value(),
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version or "2024-02-15-preview",
            )
            self._azure_model = settings.azure_openai_embeddings_deployment
        elif settings.openai_api_key:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        """Return embeddings for a batch of texts."""
        batch = [self._sanitize(text) for text in texts]
        if not batch:
            return []

        if self._azure_client and self._azure_model:
            try:
                response = await self._azure_client.embeddings.create(
                    input=batch,
                    model=self._azure_model,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("Azure OpenAI embeddings failed; using fallback heuristic.", exc_info=exc)

        if self._openai_client:
            try:
                response = await self._openai_client.embeddings.create(
                    input=batch,
                    model=self._openai_model,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("OpenAI embeddings failed; using fallback heuristic.", exc_info=exc)

        return [self._heuristic_embedding(text) for text in batch]

    async def embed_query(self, text: str) -> list[float]:
        """Return a single embedding vector for the supplied query text."""
        vectors = await self.embed_texts([text])
        return vectors[0] if vectors else [0.0] * self._FALLBACK_DIMENSIONS

    def cosine_similarity(self, vector: Sequence[float], other: Sequence[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vector or not other:
            return 0.0

        dot = sum(a * b for a, b in zip(vector, other))
        norm_a = math.sqrt(sum(a * a for a in vector))
        norm_b = math.sqrt(sum(b * b for b in other))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def _heuristic_embedding(self, text: str) -> list[float]:
        """Generate a repeatable pseudo-embedding without external APIs."""
        vector = [0.0] * self._FALLBACK_DIMENSIONS
        if not text:
            return vector

        tokens = self._tokenize(text)
        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            for index in range(self._FALLBACK_DIMENSIONS):
                byte_value = digest[index % len(digest)]
                # Map byte (0-255) to [-1, 1]
                vector[index] += (byte_value / 127.5) - 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def _tokenize(self, text: str) -> list[str]:
        normalized = (
            text.replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .strip()
        )
        if not normalized:
            return []
        # Split by whitespace while preserving Chinese characters as tokens.
        tokens: list[str] = []
        buffer = ""
        for char in normalized:
            if char.isspace():
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                continue
            if "\u4e00" <= char <= "\u9fff":
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                tokens.append(char)
            else:
                buffer += char.lower()
        if buffer:
            tokens.append(buffer)
        return tokens

    def _sanitize(self, text: str) -> str:
        return text.strip() if text else ""
