from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistFilter,
    TherapistListResponse,
    TherapistSummary,
)


class TherapistService:
    """Therapist directory interactions (stubbed with static data)."""

    _SEED_THERAPISTS = [
        TherapistDetailResponse(
            therapist_id="th_liu",
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
            therapist_id="th_wang",
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
        filtered = []
        for therapist in self._SEED_THERAPISTS:
            if filters.specialty and filters.specialty not in therapist.specialties:
                continue
            if filters.language and filters.language not in therapist.languages:
                continue
            if (
                filters.price_max is not None
                and therapist.price_per_session > filters.price_max
            ):
                continue
            filtered.append(
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
            )

        return TherapistListResponse(items=filtered)

    async def get_therapist(self, therapist_id: str) -> TherapistDetailResponse:
        for therapist in self._SEED_THERAPISTS:
            if therapist.therapist_id == therapist_id:
                return therapist
        raise ValueError(f"Therapist {therapist_id} not found")
