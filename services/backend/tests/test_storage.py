from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from app.core.config import AppSettings
from app.integrations.storage import ChatTranscriptStorage, SummaryStorage


class StubS3Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def put_object(self, **kwargs) -> None:
        self.calls.append(kwargs)


class StubS3ContextManager:
    def __init__(self, client: StubS3Client) -> None:
        self._client = client

    async def __aenter__(self) -> StubS3Client:
        return self._client

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_persist_transcript_no_bucket_returns_none() -> None:
    settings = AppSettings()
    storage = ChatTranscriptStorage(settings)

    key = await storage.persist_transcript(
        session_id=uuid4(),
        user_id=uuid4(),
        messages=[{"role": "user", "content": "hello"}],
    )

    assert key is None


@pytest.mark.asyncio
async def test_persist_transcript_uploads_to_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    client = StubS3Client()
    monkeypatch.setattr(
        "app.integrations.storage.aioboto3.client",
        lambda *args, **kwargs: StubS3ContextManager(client),
        raising=False,
    )

    settings = AppSettings(
        S3_CONVERSATION_LOGS_BUCKET="mindwell-logs",
        S3_CONVERSATION_LOGS_PREFIX="transcripts/",
        AWS_REGION="ap-southeast-1",
    )
    storage = ChatTranscriptStorage(settings)

    key = await storage.persist_transcript(
        session_id=uuid4(),
        user_id=uuid4(),
        messages=[{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
    )

    assert key is not None
    assert key.startswith("transcripts/")
    assert client.calls

    call = client.calls[0]
    assert call["Bucket"] == "mindwell-logs"
    assert call["ContentType"] == "application/json"


@pytest.mark.asyncio
async def test_summary_storage_persists_daily_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = StubS3Client()
    monkeypatch.setattr(
        "app.integrations.storage.aioboto3.client",
        lambda *args, **kwargs: StubS3ContextManager(client),
        raising=False,
    )

    settings = AppSettings(
        S3_SUMMARIES_BUCKET="mindwell-summaries",
        AWS_REGION="ap-southeast-1",
    )
    storage = SummaryStorage(settings)

    summary_key = await storage.persist_daily_summary(
        user_id=uuid4(),
        summary_date=date(2025, 1, 10),
        payload={"title": "今日回顾"},
    )

    assert summary_key.startswith("daily/")
    parts = summary_key.split("/")
    assert parts[0] == "daily"
    assert parts[-1] == "2025-01-10.json"
    assert client.calls
    call = client.calls[0]
    assert call["Bucket"] == "mindwell-summaries"
    assert call["Key"] == summary_key
    assert call["ContentType"] == "application/json"
    stored_payload = json.loads(call["Body"].decode("utf-8"))
    assert stored_payload["title"] == "今日回顾"
