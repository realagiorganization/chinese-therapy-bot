from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.agents.data_sync import DataSyncAgent, SecretMirrorMapping, SyncResult
from app.core.config import AppSettings


class StubSource:
    """Test double returning canned therapist payloads."""

    def __init__(self, records: list[dict[str, object]], name: str = "stub-source") -> None:
        self._records = records
        self.name = name

    async def fetch(self) -> list[dict[str, object]]:
        return list(self._records)


class CapturingS3Client:
    def __init__(self, calls: list[dict[str, object]]):
        self._calls = calls

    async def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        payload = json.loads(Body.decode("utf-8"))
        self._calls.append(
            {
                "bucket": Bucket,
                "key": Key,
                "body": payload,
                "content_type": ContentType,
            }
        )


class FakeSecretsManagerClient:
    def __init__(self, secrets: dict[str, str]):
        self._secrets = secrets
        self.requested: list[str] = []

    async def get_secret_value(self, *, SecretId: str) -> dict[str, Any]:
        self.requested.append(SecretId)
        if SecretId not in self._secrets:
            raise ValueError(f"Secret {SecretId} not found.")
        return {
            "ARN": f"arn:aws:secretsmanager:::secret:{SecretId}",
            "Name": SecretId,
            "SecretString": self._secrets[SecretId],
            "VersionId": "1",
        }


class FakeKeyVaultClient:
    def __init__(self) -> None:
        self.set_calls: list[tuple[str, str]] = []

    async def set_secret(self, name: str, value: str) -> None:
        self.set_calls.append((name, value))


def build_agent(
    calls: list[dict[str, object]],
    *,
    metrics_path: str | None = None,
    secrets_manager_factory: Callable[[], AsyncIterator[Any]] | None = None,
    key_vault_factory: Callable[[], AsyncIterator[Any]] | None = None,
    azure_key_vault_name: str = "kv-mindwell-test",
) -> DataSyncAgent:
    settings_kwargs: dict[str, object] = {
        "S3_BUCKET_THERAPISTS": "test-bucket",
        "AWS_REGION": "ap-east-1",
        "AZURE_KEY_VAULT_NAME": azure_key_vault_name,
    }
    if metrics_path:
        settings_kwargs["DATA_SYNC_METRICS_PATH"] = metrics_path

    settings = AppSettings(**settings_kwargs)

    @asynccontextmanager
    async def factory() -> AsyncIterator[CapturingS3Client]:
        yield CapturingS3Client(calls)

    agent = DataSyncAgent(
        settings,
        s3_client_factory=factory,
        secrets_manager_factory=secrets_manager_factory,
        key_vault_client_factory=key_vault_factory,
    )
    return agent


@pytest.mark.asyncio
async def test_data_sync_agent_writes_normalized_profiles() -> None:
    calls: list[dict[str, object]] = []
    agent = build_agent(calls)
    source = StubSource(
        records=[
            {
                "id": "therapist-001",
                "name": "刘心语",
                "specialties": ["焦虑管理", "认知行为疗法"],
                "languages": ["zh-CN"],
                "price_per_session": "680",
                "currency": "cny",
                "locale": "zh-CN",
                "profile_image_url": "https://example.com/avatar.jpg",
            },
            {
                "name": "Jane Doe",
                "languages": "en-US,zh-CN",
                "specialties": "Anxiety, Depression",
                "price": 520,
                "featured": True,
                "locale": "en-US",
            },
        ]
    )

    result = await agent.run([source], dry_run=False, prefix="therapists")

    assert isinstance(result, SyncResult)
    assert result.total_raw == 2
    assert result.normalized == 2
    assert result.written == 2
    assert result.errors == []
    assert len(calls) == 2

    slugs = {call["body"]["slug"] for call in calls}
    assert slugs == {"therapist-001", "jane-doe"}

    jane_record = next(call for call in calls if call["body"]["slug"] == "jane-doe")
    assert jane_record["body"]["languages"] == ["en-US", "zh-CN"]
    assert jane_record["body"]["specialties"] == ["Anxiety", "Depression"]
    assert jane_record["body"]["is_recommended"] is True
    assert jane_record["body"]["currency"] == "CNY"
    assert jane_record["body"]["price_per_session"] == 520


@pytest.mark.asyncio
async def test_data_sync_agent_dry_run_skips_uploads() -> None:
    calls: list[dict[str, object]] = []
    agent = build_agent(calls)
    source = StubSource(
        records=[
            {"name": "Test Therapist", "specialties": ["CBT"]},
        ]
    )

    result = await agent.run([source], dry_run=True)

    assert result.total_raw == 1
    assert result.normalized == 1
    assert result.written == 0
    assert result.errors == []
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path_is_directory", [False, True])
async def test_data_sync_agent_records_metrics(tmp_path, path_is_directory: bool) -> None:
    calls: list[dict[str, object]] = []
    metrics_path = tmp_path / "metrics.json"
    if path_is_directory:
        metrics_path = tmp_path / "metrics-dir"

    agent = build_agent(calls, metrics_path=str(metrics_path))
    source = StubSource(
        records=[
            {"name": "Metrics Therapist", "specialties": ["CBT"]},
        ]
    )

    result = await agent.run([source], dry_run=True)

    expected_file = metrics_path if metrics_path.suffix else metrics_path / "data_sync_metrics.json"
    assert expected_file.exists()

    payload = json.loads(expected_file.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["bucket"] == "test-bucket"
    assert payload["source_count"] == 1
    assert payload["sources"] == ["stub-source"]
    assert payload["result"]["total_raw"] == result.total_raw == 1
    assert payload["result"]["normalized"] == result.normalized == 1
    assert payload["result"]["written"] == 0
    assert payload["result"]["errors"] == []


@pytest.mark.asyncio
async def test_data_sync_agent_mirror_secrets_updates_key_vault(tmp_path) -> None:
    secrets_client = FakeSecretsManagerClient(
        {"mindwell/dev/openai/api-key": "sk-prod-123456789"}
    )
    key_vault_client = FakeKeyVaultClient()

    @asynccontextmanager
    async def secrets_factory() -> AsyncIterator[FakeSecretsManagerClient]:
        yield secrets_client

    @asynccontextmanager
    async def key_vault_factory() -> AsyncIterator[FakeKeyVaultClient]:
        yield key_vault_client

    agent = build_agent(
        [],
        metrics_path=str(tmp_path),
        secrets_manager_factory=secrets_factory,
        key_vault_factory=key_vault_factory,
    )

    mappings = [
        SecretMirrorMapping(
            source_secret_id="mindwell/dev/openai/api-key",
            target_secret_name="openai-api-key",
        )
    ]

    results = await agent.mirror_secrets(mappings, dry_run=False)

    assert results
    assert results[0].status == "updated"
    assert key_vault_client.set_calls == [("openai-api-key", "sk-prod-123456789")]

    metrics_file = tmp_path / "data_sync_secret_metrics.json"
    assert metrics_file.exists()
    payload = json.loads(metrics_file.read_text(encoding="utf-8"))
    assert payload["result_count"] == 1
    assert payload["results"][0]["status"] == "updated"
    assert payload["results"][0]["target_secret_name"] == "openai-api-key"


@pytest.mark.asyncio
async def test_data_sync_agent_mirror_secrets_dry_run(tmp_path) -> None:
    secrets_client = FakeSecretsManagerClient(
        {"mindwell/dev/openai/api-key": "sk-stage-abcdef"}
    )
    key_vault_client = FakeKeyVaultClient()

    @asynccontextmanager
    async def secrets_factory() -> AsyncIterator[FakeSecretsManagerClient]:
        yield secrets_client

    @asynccontextmanager
    async def key_vault_factory() -> AsyncIterator[FakeKeyVaultClient]:
        yield key_vault_client

    agent = build_agent(
        [],
        metrics_path=str(tmp_path),
        secrets_manager_factory=secrets_factory,
        key_vault_factory=key_vault_factory,
    )

    mappings = [
        SecretMirrorMapping(
            source_secret_id="mindwell/dev/openai/api-key",
            target_secret_name="openai-api-key",
        )
    ]

    results = await agent.mirror_secrets(mappings, dry_run=True)

    assert results
    assert results[0].status == "skipped"
    assert results[0].message.startswith("Dry run")
    assert key_vault_client.set_calls == []

    metrics_file = tmp_path / "data_sync_secret_metrics.json"
    assert metrics_file.exists()
    payload = json.loads(metrics_file.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["results"][0]["status"] == "skipped"
