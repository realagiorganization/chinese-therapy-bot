from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db_session
from app.core.app import create_app
from app.models.entities import PilotCohortParticipant
from app.schemas.pilot_cohort import PilotParticipantStatus


@pytest_asyncio.fixture()
async def cohort_client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PilotCohortParticipant.__table__.create)

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


def test_create_pilot_participant_returns_entry(cohort_client: TestClient) -> None:
    response = cohort_client.post(
        "/api/pilot-cohort/participants",
        json={
            "cohort": "pilot-2025w6",
            "participant_alias": "Alice",
            "contact_email": "alice@example.com",
            "channel": "web",
            "status": "invited",
            "tags": ["sleep"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["cohort"] == "pilot-2025w6"
    assert payload["participant_alias"] == "Alice"
    assert payload["status"] == "invited"
    assert payload["metadata"] == {}


def test_list_pilot_participants_applies_status_filter(cohort_client: TestClient) -> None:
    for status in ("invited", "active"):
        resp = cohort_client.post(
            "/api/pilot-cohort/participants",
            json={
                "cohort": "pilot-2025w7",
                "participant_alias": f"User-{status}",
                "contact_email": f"{status}@example.com",
                "status": status,
            },
        )
        assert resp.status_code == 201

    response = cohort_client.get(
        "/api/pilot-cohort/participants",
        params={"cohort": "pilot-2025w7", "status": "active"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["participant_alias"] == "User-active"


def test_update_pilot_participant_allows_status_transition(cohort_client: TestClient) -> None:
    create_resp = cohort_client.post(
        "/api/pilot-cohort/participants",
        json={
            "cohort": "pilot-2025w8",
            "participant_alias": "Dana",
            "contact_email": "dana@example.com",
        },
    )
    assert create_resp.status_code == 201
    participant_id = create_resp.json()["id"]

    update_resp = cohort_client.patch(
        f"/api/pilot-cohort/participants/{participant_id}",
        json={
            "status": "active",
            "consent_received": True,
            "tags": ["journey"],
        },
    )

    assert update_resp.status_code == 200
    payload = update_resp.json()
    assert payload["status"] == "active"
    assert payload["consent_received"] is True
    assert payload["tags"] == ["journey"]


def test_followups_endpoint_returns_plan(cohort_client: TestClient) -> None:
    invite_sent_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    cohort_client.post(
        "/api/pilot-cohort/participants",
        json={
            "cohort": "pilot-2025w11",
            "participant_alias": "Elena",
            "contact_email": "elena@example.com",
            "status": "invited",
            "locale": "en-US",
            "channel": "email",
            "invite_sent_at": invite_sent_at,
        },
    )
    # Participant outside the filtered cohort should be ignored.
    cohort_client.post(
        "/api/pilot-cohort/participants",
        json={
            "cohort": "pilot-2025w12",
            "participant_alias": "Ming",
            "status": "invited",
            "invite_sent_at": invite_sent_at,
        },
    )

    response = cohort_client.get(
        "/api/pilot-cohort/participants/followups",
        params={"cohort": "pilot-2025w11", "horizon_days": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["cohort"] == "pilot-2025w11"
    assert item["status"] == PilotParticipantStatus.INVITED.value
    assert item["subject"] == "MindWell pilot invitation check-in"
    assert item["urgency"] in {"due", "overdue"}
