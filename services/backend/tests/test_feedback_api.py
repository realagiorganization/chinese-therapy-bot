from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db_session
from app.core.app import create_app
from app.models.entities import PilotFeedback, PilotParticipant, User


@pytest_asyncio.fixture()
async def feedback_client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(PilotParticipant.__table__.create)
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
    participant_resp = feedback_client.post(
        "/api/feedback/pilot/participants",
        json={
            "cohort": "pilot-2025w4",
            "full_name": "Pilot User",
            "contact_email": "pilot@example.com",
            "status": "invited",
        },
    )
    assert participant_resp.status_code == 201
    participant_id = participant_resp.json()["id"]

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
            "participant_id": participant_id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["cohort"] == "pilot-2025w4"
    assert payload["tags"] == ["journey"]
    assert payload["trust_score"] == 5
    assert payload["metadata"] == {}
    assert payload["participant_id"] == participant_id


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


def test_pilot_participant_endpoints_support_filters_and_updates(feedback_client: TestClient) -> None:
    create_body = {
        "cohort": "pilot-2025w4",
        "full_name": "Alice",
        "contact_email": "alice@example.com",
        "tags": ["priority"],
        "requires_follow_up": True,
        "status": "enrolled",
    }
    response = feedback_client.post("/api/feedback/pilot/participants", json=create_body)
    assert response.status_code == 201
    participant_id = response.json()["id"]

    feedback_client.post(
        "/api/feedback/pilot/participants",
        json={
            "cohort": "pilot-2025w4",
            "full_name": "Bob",
            "contact_email": "bob@example.com",
            "tags": ["later"],
            "status": "prospect",
        },
    )

    listing = feedback_client.get(
        "/api/feedback/pilot/participants",
        params={"cohort": "pilot-2025w4", "tag": "priority", "requires_follow_up": True},
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Alice"

    update_resp = feedback_client.patch(
        f"/api/feedback/pilot/participants/{participant_id}",
        json={"status": "completed", "requires_follow_up": False, "tags": ["closed"]},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "completed"
    assert updated["tags"] == ["closed"]


def test_get_pilot_backlog_returns_prioritised_items(feedback_client: TestClient) -> None:
    feedback_client.post(
        "/api/feedback/pilot",
        json={
            "cohort": "pilot-2025w4",
            "channel": "web",
            "role": "participant",
            "sentiment_score": 2,
            "trust_score": 2,
            "usability_score": 2,
            "severity": "critical",
            "tags": ["latency"],
            "blockers": "Streaming froze for 20s.",
            "follow_up_needed": True,
        },
    )
    feedback_client.post(
        "/api/feedback/pilot",
        json={
            "cohort": "pilot-2025w4",
            "channel": "mobile",
            "role": "participant",
            "sentiment_score": 4,
            "trust_score": 3,
            "usability_score": 3,
            "severity": "medium",
            "tags": ["latency"],
        },
    )
    feedback_client.post(
        "/api/feedback/pilot",
        json={
            "cohort": "pilot-2025w4",
            "channel": "web",
            "role": "participant",
            "sentiment_score": 5,
            "trust_score": 5,
            "usability_score": 5,
            "severity": "low",
            "tags": ["delight"],
            "highlights": "Great onboarding messages.",
        },
    )

    response = feedback_client.get(
        "/api/feedback/pilot/backlog",
        params={"cohort": "pilot-2025w4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["label"] == "latency"
    assert payload["items"][0]["representative_severity"] == "critical"
    assert payload["items"][0]["follow_up_count"] == 1
