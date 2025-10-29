from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Therapist as TherapistModel
from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistFilter,
    TherapistListResponse,
    TherapistSummary,
)


class TherapistService:
    """Therapist directory interactions backed by persistence with static fallback."""

    def __init__(self, session: AsyncSession):
        self._session = session

    _SEED_THERAPISTS = [
        TherapistDetailResponse(
            therapist_id="00000000-0000-0000-0000-000000000101",
            name="刘心语",
            title="注册心理咨询师",
            specialties=["认知行为疗法", "焦虑管理"],
            languages=["zh-CN"],
            price_per_session=680.0,
            biography="拥有 8 年临床经验，擅长职场压力与情绪调节。",
            availability=["2025-01-10T02:00:00Z", "2025-01-12T10:00:00Z"],
            is_recommended=True,
        ),
        TherapistDetailResponse(
            therapist_id="00000000-0000-0000-0000-000000000102",
            name="王晨",
            title="国家二级心理咨询师",
            specialties=["家庭治疗", "青少年成长"],
            languages=["zh-CN", "en-US"],
            price_per_session=520.0,
            biography="关注家庭关系修复，结合正念减压技巧。",
            availability=["2025-01-11T08:00:00Z"],
        ),
    ]

    async def list_therapists(self, filters: TherapistFilter) -> TherapistListResponse:
        therapists = await self._load_therapists()
        filtered = [
            therapist for therapist in therapists if self._matches_filters(therapist, filters)
        ]

        return TherapistListResponse(items=filtered)

    async def get_therapist(self, therapist_id: str) -> TherapistDetailResponse:
        therapists = await self._load_therapists(detail=True)
        for therapist in therapists:
            if therapist.therapist_id == therapist_id:
                return therapist
        raise ValueError(f"Therapist {therapist_id} not found")

    async def _load_therapists(
        self, detail: bool = False
    ) -> Sequence[TherapistSummary | TherapistDetailResponse]:
        stmt = select(TherapistModel)
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return self._SEED_THERAPISTS if detail else self._seed_as_summaries()

        if detail:
            return [
                TherapistDetailResponse(
                    therapist_id=str(record.id),
                    name=record.name,
                    title=record.title,
                    specialties=record.specialties or [],
                    languages=record.languages or [],
                    price_per_session=record.price_per_session or 0.0,
                    biography=record.biography or "",
                    availability=[],
                    is_recommended=record.is_recommended,
                )
                for record in records
            ]

        return [
            TherapistSummary(
                therapist_id=str(record.id),
                name=record.name,
                title=record.title,
                specialties=record.specialties or [],
                languages=record.languages or [],
                price_per_session=record.price_per_session or 0.0,
                currency=record.currency,
                is_recommended=record.is_recommended,
            )
            for record in records
        ]

    def _seed_as_summaries(self) -> list[TherapistSummary]:
        return [
            TherapistSummary(
                therapist_id=therapist.therapist_id,
                name=therapist.name,
                title=therapist.title,
                specialties=therapist.specialties,
                languages=therapist.languages,
                price_per_session=therapist.price_per_session,
                currency=therapist.currency,
                is_recommended=therapist.is_recommended,
            )
            for therapist in self._SEED_THERAPISTS
        ]

    def _matches_filters(
        self, therapist: TherapistSummary | TherapistDetailResponse, filters: TherapistFilter
    ) -> bool:
        if filters.specialty:
            specialty = filters.specialty.lower()
            if not any(s.lower() == specialty for s in therapist.specialties):
                return False
        if filters.language:
            language = filters.language.lower()
            if not any(lang.lower() == language for lang in therapist.languages):
                return False
        if filters.price_max is not None and therapist.price_per_session > filters.price_max:
            return False
        return True
