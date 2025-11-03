from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_mood_service
from app.core.app import create_app
from app.services.mood import MoodSummary, MoodTrendPoint


class StubMoodService:
    def __init__(self) -> None:
        now = datetime(2025, 1, 15, 8, 30, tzinfo=timezone.utc)
        identifier = str(uuid4())
        self.record = SimpleNamespace(
            id=identifier,
            user_id=str(uuid4()),
            score=4,
            energy_level=3,
            emotion="平静",
            tags=["呼吸练习"],
            note="感觉好一些了",
            context={"trigger": "morning_routine"},
            check_in_at=now,
            created_at=now,
            updated_at=now,
        )
        self.summary = MoodSummary(
            average_score=4.2,
            sample_count=3,
            streak_days=2,
            trend=[
                MoodTrendPoint(date(2025, 1, 13), 3.5, 2),
                MoodTrendPoint(date(2025, 1, 14), 4.0, 1),
                MoodTrendPoint(date(2025, 1, 15), 5.0, 1),
            ],
            last_check_in=self.record,
        )
        self.create_calls: list[dict[str, object]] = []
        self.last_limit = None
        self.last_window = None
        self.raise_error = False

    async def create_check_in(self, user_id: str, **kwargs):
        if self.raise_error:
            raise ValueError("invalid data")
        payload = {"user_id": user_id, **kwargs}
        self.create_calls.append(payload)
        return self.record

    async def list_check_ins(self, user_id: str, *, limit: int):
        self.last_limit = limit
        if self.raise_error:
            raise ValueError("invalid")
        return [self.record]

    async def summarize(self, user_id: str, *, window_days: int):
        self.last_window = window_days
        if self.raise_error:
            raise ValueError("invalid")
        return self.summary


@contextmanager
def client_with_service(service: StubMoodService):
    app = create_app()

    async def override_service():
        return service

    app.dependency_overrides[get_mood_service] = override_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_create_mood_check_in_returns_created_payload() -> None:
    service = StubMoodService()
    user_id = str(uuid4())
    payload = {"score": 4, "energy_level": 3, "note": "感觉好一些", "tags": ["自我关怀"]}

    with client_with_service(service) as client:
        response = client.post(
            f"/api/mood/{user_id}/check-ins",
            json=payload,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 4
    assert body["tags"]
    assert service.create_calls
    assert service.create_calls[0]["user_id"] == user_id


def test_list_mood_check_ins_returns_items_and_summary() -> None:
    service = StubMoodService()
    user_id = str(uuid4())

    with client_with_service(service) as client:
        response = client.get(
            f"/api/mood/{user_id}/check-ins",
            params={"limit": 5, "window_days": 10},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["average_score"] == pytest.approx(4.2)
    assert body["summary"]["streak_days"] == 2
    assert body["items"][0]["id"] == service.record.id
    assert service.last_limit == 5
    assert service.last_window == 10


def test_mood_routes_surface_validation_errors_as_bad_request() -> None:
    service = StubMoodService()
    service.raise_error = True
    user_id = str(uuid4())

    with client_with_service(service) as client:
        response = client.post(
            f"/api/mood/{user_id}/check-ins",
            json={"score": 2},
        )
    assert response.status_code == 400

    with client_with_service(service) as client:
        response = client.get(f"/api/mood/{user_id}/check-ins")
    assert response.status_code == 400

    with client_with_service(service) as client:
        response = client.get(f"/api/mood/{user_id}/summary")
    assert response.status_code == 400
