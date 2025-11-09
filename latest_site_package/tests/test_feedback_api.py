from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db_session
from app.core.app import create_app
from app.models.entities import PilotFeedback, User


@pytest_asyncio.fixture()
async def feedback_client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(PilotFeedback.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app()

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


def test_submit_pilot_feedback_returns_created_entry(feedback_client: TestClient) -> None:
    response = feedback_client.post(
        "/api/feedback/pilot",
        json={
            "cohort": "pilot-2025w4",
            "channel": "web",
            "role": "participant",
            "scenario": "journey-dashboard",
            "sentiment_score": 4,
            "trust_score": 5,
            "usability_score": 4,
            "tags": ["journey"],
            "highlights": "Loved the spotlight summary.",
            "blockers": "",
            "follow_up_needed": False,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["cohort"] == "pilot-2025w4"
    assert payload["tags"] == ["journey"]
    assert payload["trust_score"] == 5
    assert payload["metadata"] == {}


def test_list_pilot_feedback_filters_by_query(feedback_client: TestClient) -> None:
    for channel, trust in (("web", 5), ("mobile", 2)):
        resp = feedback_client.post(
            "/api/feedback/pilot",
            json={
                "cohort": "pilot-2025w4",
                "channel": channel,
                "role": "participant",
                "sentiment_score": 4,
                "trust_score": trust,
                "usability_score": 3,
                "tags": ["latency"],
            },
        )
        assert resp.status_code == 201

    response = feedback_client.get(
        "/api/feedback/pilot",
        params={"cohort": "pilot-2025w4", "minimum_trust_score": 4},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["channel"] == "web"
