from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import Therapist, TherapistLocalization
from app.schemas.therapists import TherapistFilter
from app.services.therapists import TherapistService


async def _seed_directory(session: AsyncSession) -> None:
    therapists: list[Therapist] = []
    for index, price in enumerate((420.0, 580.0, 760.0), start=1):
        therapist = Therapist(
            id=uuid4(),
            slug=f"therapist-{index}",
            name=f"Therapist {index}",
            title="注册心理咨询师",
            specialties=["焦虑管理", "家庭治疗"] if index == 2 else ["焦虑管理"],
            languages=["zh-CN"] if index != 2 else ["zh-CN", "en-US"],
            price_per_session=price,
            currency="CNY",
            biography=f"Sample biography {index}",
            is_recommended=index != 2,
            availability=["2025-01-10T02:00:00Z"],
        )
        therapist.localizations = [
            TherapistLocalization(
                therapist_id=therapist.id,
                locale="zh-CN",
                title=therapist.title,
                biography=therapist.biography,
            )
        ]
        therapists.append(therapist)

    session.add_all(therapists)
    await session.commit()


async def _with_service(
    callback: Callable[[TherapistService], Awaitable[None]],
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Therapist.__table__.create)
            await conn.run_sync(TherapistLocalization.__table__.create)

        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with session_factory() as session:
            await _seed_directory(session)
            service = TherapistService(session)
            await callback(service)
    finally:
        await engine.dispose()


def test_list_therapists_respects_price_minimum() -> None:
    async def _assert(service: TherapistService) -> None:
        response = await service.list_therapists(
            TherapistFilter(price_min=500.0, locale="zh-CN")
        )
        assert [item.name for item in response.items] == ["Therapist 2", "Therapist 3"]
        assert all(item.price_per_session >= 500.0 for item in response.items)

    asyncio.run(_with_service(_assert))


def test_list_therapists_respects_price_range() -> None:
    async def _assert(service: TherapistService) -> None:
        response = await service.list_therapists(
            TherapistFilter(price_min=500.0, price_max=700.0, locale="zh-CN")
        )
        assert [item.name for item in response.items] == ["Therapist 2"]
        assert response.items[0].price_per_session == 580.0

    asyncio.run(_with_service(_assert))
