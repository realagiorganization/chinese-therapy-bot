from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db_session
from app.core.app import create_app
from app.models.entities import PilotCohortParticipant, PilotUATSession


@pytest_asyncio.fixture()
async def uat_client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PilotCohortParticipant.__table__.create)
        await conn.run_sync(PilotUATSession.__table__.create)

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


def test_log_pilot_uat_session_returns_created_entry(uat_client: TestClient) -> None:
    response = uat_client.post(
        "/api/uat/sessions",
        json={
            "cohort": "pilot-2025w9",
            "participant_alias": "Ming",
            "facilitator": "QA",
            "scenario": "journey-dashboard",
            "environment": "qa",
            "platform": "web",
            "satisfaction_score": 4,
            "trust_score": 3,
            "issues": [{"title": "Latency", "severity": "High"}],
            "action_items": ["Review caching"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["cohort"] == "pilot-2025w9"
    assert payload["issues"][0]["severity"] == "high"
    assert payload["metadata"] == {}


def test_list_pilot_uat_sessions_supports_filters(uat_client: TestClient) -> None:
    timestamps = [
        datetime(2025, 1, 9, tzinfo=timezone.utc).isoformat(),
        datetime(2025, 1, 10, tzinfo=timezone.utc).isoformat(),
    ]
    for timestamp, env in zip(timestamps, ("qa", "pilot"), strict=True):
        resp = uat_client.post(
            "/api/uat/sessions",
            json={
                "cohort": "pilot-2025w10",
                "participant_alias": f"user-{env}",
                "environment": env,
                "platform": "mobile",
                "session_date": timestamp,
                "satisfaction_score": 4,
                "issues": [],
            },
        )
        assert resp.status_code == 201

    response = uat_client.get(
        "/api/uat/sessions",
        params={
            "cohort": "pilot-2025w10",
            "environment": "qa",
            "occurred_before": timestamps[1],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["participant_alias"] == "user-qa"


def test_pilot_uat_summary_returns_aggregates(uat_client: TestClient) -> None:
    entries = [
        {
            "cohort": "pilot-2025w11",
            "environment": "qa",
            "platform": "web",
            "satisfaction_score": 5,
            "trust_score": 4,
            "issues": [{"title": "Latency", "severity": "High"}],
        },
        {
            "cohort": "pilot-2025w11",
            "environment": "qa",
            "platform": "mobile",
            "satisfaction_score": 3,
            "trust_score": 2,
            "blockers": "Audio muted.",
        },
    ]
    for payload in entries:
        resp = uat_client.post("/api/uat/sessions", json=payload)
        assert resp.status_code == 201

    response = uat_client.get(
        "/api/uat/sessions/summary",
        params={"cohort": "pilot-2025w11"},
    )

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_sessions"] == 2
    assert summary["sessions_with_blockers"] == 1
    assert summary["issues_by_severity"][0] == {"severity": "high", "count": 1}
