from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pytest

from app.agents.retention_cleanup import RetentionCleanupAgent
from app.core.config import AppSettings


class StubS3Client:
    def __init__(self, store: dict[str, list[dict[str, Any]]]) -> None:
        self.store = store
        self.delete_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, str]] = []

    async def list_objects_v2(self, *, Bucket: str, Prefix: str, **_: Any) -> dict[str, Any]:
        self.list_calls.append({"Bucket": Bucket, "Prefix": Prefix})
        objects = [
            obj
            for obj in self.store.get(Bucket, [])
            if obj["Key"].startswith(Prefix)
        ]
        return {"Contents": list(objects), "IsTruncated": False}

    async def delete_objects(self, *, Bucket: str, Delete: dict[str, Any], **_: Any) -> dict[str, Any]:
        objects = Delete.get("Objects", [])
        keys = {entry["Key"] for entry in objects}
        self.delete_calls.append({"Bucket": Bucket, "Keys": list(keys)})
        retained = [
            obj for obj in self.store.get(Bucket, []) if obj["Key"] not in keys
        ]
        self.store[Bucket] = retained
        return {"Deleted": [{"Key": key} for key in keys]}


def build_factory(store: dict[str, list[dict[str, Any]]]) -> Any:
    client = StubS3Client(store)

    @asynccontextmanager
    async def factory() -> Any:
        yield client

    return factory, client


def make_object(key: str, *, year: int, month: int, day: int) -> dict[str, Any]:
    return {
        "Key": key,
        "LastModified": datetime(year, month, day, tzinfo=timezone.utc),
        "Size": 1024,
    }


@pytest.mark.asyncio
async def test_dry_run_reports_candidates_without_deletion() -> None:
    store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    store["mindwell-logs"].append(
        make_object("conversations/session-1/stream/000001_20230101T000000Z.json", year=2023, month=1, day=1)
    )
    store["mindwell-summaries"].append(
        make_object("daily/550e8400-e29b-41d4-a716-446655440000/2023-01-01.json", year=2023, month=1, day=2)
    )

    factory, client = build_factory(store)
    now = datetime(2025, 6, 1, tzinfo=timezone.utc)
    settings = AppSettings(
        S3_CONVERSATION_LOGS_BUCKET="mindwell-logs",
        S3_CONVERSATION_LOGS_PREFIX="conversations",
        S3_SUMMARIES_BUCKET="mindwell-summaries",
    )

    agent = RetentionCleanupAgent(
        settings,
        s3_client_factory=factory,
        now_factory=lambda: now,
    )

    results = await agent.run(dry_run=True)

    conversations = results["conversations"]
    summaries = results["daily_summaries"]

    assert conversations.delete_candidates == 1
    assert conversations.deleted == 0
    assert conversations.deleted_keys == [
        "conversations/session-1/stream/000001_20230101T000000Z.json"
    ]
    assert summaries.delete_candidates == 1
    assert summaries.deleted == 0
    assert not client.delete_calls


@pytest.mark.asyncio
async def test_execute_deletes_objects_older_than_retention() -> None:
    store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    store["mindwell-logs"].extend(
        [
            make_object(
                "conversations/session-2/stream/000001_20220501T000000Z.json",
                year=2022,
                month=5,
                day=1,
            ),
            make_object(
                "conversations/session-2/stream/000002_20241201T000000Z.json",
                year=2024,
                month=12,
                day=1,
            ),
            make_object(
                "conversations/session-2/stream/000003_20250501T000000Z.json",
                year=2025,
                month=5,
                day=1,
            ),
        ]
    )
    store["mindwell-summaries"].extend(
        [
            make_object(
                "daily/550e8400-e29b-41d4-a716-446655440001/2023-01-01.json",
                year=2023,
                month=1,
                day=2,
            ),
            make_object(
                "daily/550e8400-e29b-41d4-a716-446655440001/2025-04-01.json",
                year=2025,
                month=4,
                day=1,
            ),
        ]
    )

    factory, client = build_factory(store)
    now = datetime(2025, 6, 1, tzinfo=timezone.utc)
    settings = AppSettings(
        S3_CONVERSATION_LOGS_BUCKET="mindwell-logs",
        S3_CONVERSATION_LOGS_PREFIX="conversations",
        S3_SUMMARIES_BUCKET="mindwell-summaries",
    )

    agent = RetentionCleanupAgent(
        settings,
        s3_client_factory=factory,
        now_factory=lambda: now,
    )

    results = await agent.run(dry_run=False)

    conversations = results["conversations"]
    summaries = results["daily_summaries"]

    assert conversations.delete_candidates == 1
    assert conversations.deleted == 1
    assert conversations.archive_candidates == 2
    assert "conversations/session-2/stream/000001_20220501T000000Z.json" not in [
        obj["Key"] for obj in store["mindwell-logs"]
    ]

    assert summaries.delete_candidates == 1
    assert summaries.deleted == 1
    assert "daily/550e8400-e29b-41d4-a716-446655440001/2023-01-01.json" not in [
        obj["Key"] for obj in store["mindwell-summaries"]
    ]
    assert client.delete_calls
