import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.integrations.embeddings import EmbeddingClient
from app.services.recommendations import TherapistRecommendationService


@pytest.mark.asyncio
async def test_recommendations_return_seed_results_when_database_empty() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    settings = AppSettings()
    embedding_client = EmbeddingClient(settings)

    async with session_factory() as session:
        service = TherapistRecommendationService(session, embedding_client)
        results = await service.recommend("我最近感到焦虑和压力很大", locale="zh-CN")

    await engine.dispose()

    assert results
    top = results[0]
    assert top.score >= 0
    assert top.reason
    assert top.name
