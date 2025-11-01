from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.embeddings import EmbeddingClient
from app.models import Therapist as TherapistModel
from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistRecommendation,
)
from app.services.therapists import TherapistService


logger = logging.getLogger(__name__)


class TherapistRecommendationService:
    """Embedding-driven therapist recommendations with heuristic fallbacks."""

    _DEFAULT_LIMIT = 3

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: EmbeddingClient,
        therapist_service: TherapistService | None = None,
    ):
        self._session = session
        self._embedding_client = embedding_client
        self._therapist_service = therapist_service or TherapistService(session)

    async def recommend(
        self,
        query: str,
        *,
        locale: str = "zh-CN",
        limit: int | None = None,
    ) -> list[TherapistRecommendation]:
        if not query:
            return []

        therapists = await self._load_therapists(locale=locale)
        if not therapists:
            return []

        documents = [self._make_document(therapist) for therapist in therapists]
        embeddings = await self._embedding_client.embed_texts(documents)
        query_vector = await self._embedding_client.embed_query(query)

        scored: list[tuple[float, TherapistDetailResponse]] = []
        for therapist, vector in zip(therapists, embeddings):
            score = self._embedding_client.cosine_similarity(query_vector, vector)
            if score <= 0:
                continue
            scored.append((score, therapist))

        if not scored:
            # No embedding matches; fall back to keyword scoring.
            scored = [
                (self._keyword_match_score(query, therapist), therapist)
                for therapist in therapists
            ]
            scored = [item for item in scored if item[0] > 0]

        scored.sort(key=lambda item: item[0], reverse=True)
        top_k = (limit or self._DEFAULT_LIMIT)
        recommendations: list[TherapistRecommendation] = []
        for score, therapist in scored[:top_k]:
            keywords = self._matched_keywords(query, therapist)
            recommendations.append(
                TherapistRecommendation(
                    therapist_id=therapist.therapist_id,
                    name=therapist.name,
                    title=therapist.title,
                    specialties=therapist.specialties,
                    languages=therapist.languages,
                    price_per_session=therapist.price_per_session,
                    currency=therapist.currency,
                    is_recommended=therapist.is_recommended,
                    score=min(max(score, 0.0), 1.0),
                    reason=self._build_reason(therapist, keywords),
                    matched_keywords=keywords,
                )
            )

        return recommendations

    async def _load_therapists(self, *, locale: str) -> list[TherapistDetailResponse]:
        stmt = select(TherapistModel).options(selectinload(TherapistModel.localizations))
        try:
            result = await self._session.execute(stmt)
            records = result.scalars().all()
        except SQLAlchemyError as exc:
            logger.debug("Therapist lookup failed; reverting to seed data: %s", exc)
            records = []

        if not records:
            # Fall back to static seed data.
            return list(self._therapist_service._SEED_THERAPISTS)  # type: ignore[attr-defined]

        detailed: list[TherapistDetailResponse] = []
        for record in records:
            detailed.append(self._therapist_service._serialize_detail(record, locale))
        return detailed

    def _make_document(self, therapist: TherapistDetailResponse) -> str:
        fragments = [
            therapist.name,
            therapist.title,
            " ".join(therapist.specialties),
            " ".join(therapist.languages),
            therapist.biography,
        ]
        return " ".join(fragment for fragment in fragments if fragment).strip()

    def _keyword_match_score(self, query: str, therapist: TherapistDetailResponse) -> float:
        keywords = self._matched_keywords(query, therapist)
        if not keywords:
            return 0.0
        return min(1.0, 0.2 * len(keywords))

    def _matched_keywords(self, query: str, therapist: TherapistDetailResponse) -> list[str]:
        lowered = query.lower()
        hits: set[str] = set()
        for specialty in therapist.specialties:
            if specialty and specialty.lower() in lowered:
                hits.add(specialty)
            if specialty and specialty in query:
                hits.add(specialty)
        for language in therapist.languages:
            if language and language.lower() in lowered:
                hits.add(language)
        return sorted(hits)

    def _build_reason(
        self,
        therapist: TherapistDetailResponse,
        keywords: Iterable[str],
    ) -> str:
        keyword_list = [keyword for keyword in keywords if keyword]
        if keyword_list:
            joined = "、".join(keyword_list)
            return f"匹配你提及的主题：{joined}。{therapist.name} 擅长相关领域。"

        core_specialties = "、".join(therapist.specialties[:3])
        return f"{therapist.name} 擅长 {core_specialties}，适合进一步深入交流。"
