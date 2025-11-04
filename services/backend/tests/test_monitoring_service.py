from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.config import AppSettings
from app.services.monitoring import MetricAlert, MonitoringService


@dataclass
class FakeAppInsightsClient:
    latency_ms: float
    error_rate: float

    async def query(self, query: str, *, timespan: str = "PT5M") -> dict:
        if "P95DurationMs" in query:
            return {
                "tables": [
                    {
                        "columns": [{"name": "P95DurationMs"}],
                        "rows": [[self.latency_ms]],
                    }
                ]
            }
        if "ErrorRate" in query:
            return {
                "tables": [
                    {
                        "columns": [{"name": "ErrorRate"}],
                        "rows": [[self.error_rate]],
                    }
                ]
            }
        raise AssertionError(f"Unexpected query: {query}")


@dataclass
class FakeCostClient:
    value: float
    start: date | None = None
    end: date | None = None

    async def unblended_cost(self, start: date, end: date) -> float:
        self.start = start
        self.end = end
        return self.value


class RecordingDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[list[MetricAlert]] = []

    async def dispatch(self, alerts: list[MetricAlert]) -> None:
        actionable = [alert for alert in alerts if alert.breached]
        if actionable:
            self.dispatched.append(actionable)


@pytest.mark.asyncio
async def test_monitoring_service_flags_threshold_breaches(tmp_path) -> None:
    data_sync_metrics = tmp_path / "data_sync_metrics.json"
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    data_sync_payload = {
        "generated_at": stale_timestamp,
        "dry_run": False,
        "bucket": "test-bucket",
        "source_count": 1,
        "sources": ["stub"],
        "result": {
            "total_raw": 10,
            "normalized": 10,
            "written": 0,
            "skipped": 0,
            "errors": ["s3 failure"],
        },
    }
    data_sync_metrics.write_text(json.dumps(data_sync_payload), encoding="utf-8")

    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=300.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
        DATA_SYNC_METRICS_PATH=str(data_sync_metrics),
        MONITORING_DATA_SYNC_MAX_AGE_HOURS=6.0,
    )
    dispatcher = RecordingDispatcher()
    service = MonitoringService(
        settings,
        app_insights_client=FakeAppInsightsClient(latency_ms=1500.0, error_rate=0.05),
        cost_client=FakeCostClient(value=450.0),
        alert_dispatcher=dispatcher,
    )

    alerts = await service.run(dispatch=True)

    status_map = {alert.metric: alert.status for alert in alerts}
    assert status_map["latency_p95_ms"] == "alert"
    assert status_map["error_rate"] == "alert"
    assert status_map["cloud_cost_usd"] == "alert"
    assert status_map["data_sync_recency_hours"] == "alert"

    assert dispatcher.dispatched, "Expected actionable alerts to be dispatched."
    dispatched_metrics = {alert.metric for alert in dispatcher.dispatched[0]}
    assert dispatched_metrics == {"latency_p95_ms", "error_rate", "cloud_cost_usd", "data_sync_recency_hours"}


@pytest.mark.asyncio
async def test_monitoring_service_ok_when_within_thresholds(tmp_path) -> None:
    data_sync_metrics = tmp_path / "ok_data_sync.json"
    fresh_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    data_sync_metrics.write_text(
        json.dumps(
            {
                "generated_at": fresh_timestamp,
                "dry_run": False,
                "bucket": "test-bucket",
                "source_count": 2,
                "sources": ["http", "csv"],
                "result": {
                    "total_raw": 20,
                    "normalized": 18,
                    "written": 18,
                    "skipped": 2,
                    "errors": [],
                },
            }
        ),
        encoding="utf-8",
    )

    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1800.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.05,
        MONITORING_COST_THRESHOLD_USD=500.0,
        MONITORING_COST_LOOKBACK_DAYS=3,
        AWS_REGION="us-east-1",
        DATA_SYNC_METRICS_PATH=str(data_sync_metrics),
        MONITORING_DATA_SYNC_MAX_AGE_HOURS=6.0,
    )
    dispatcher = RecordingDispatcher()
    service = MonitoringService(
        settings,
        app_insights_client=FakeAppInsightsClient(latency_ms=900.0, error_rate=0.01),
        cost_client=FakeCostClient(value=220.0),
        alert_dispatcher=dispatcher,
    )

    alerts = await service.run(dispatch=True)
    status_map = {alert.metric: alert.status for alert in alerts}
    assert status_map == {
        "latency_p95_ms": "ok",
        "error_rate": "ok",
        "cloud_cost_usd": "ok",
        "data_sync_recency_hours": "ok",
    }
    assert dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_monitoring_service_skips_checks_when_not_configured() -> None:
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1200.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.05,
        MONITORING_COST_THRESHOLD_USD=0.0,
        MONITORING_COST_LOOKBACK_DAYS=7,
    )
    service = MonitoringService(settings)

    alerts = await service.run(dispatch=False)
    status_map = {alert.metric: alert.status for alert in alerts}

    assert status_map["latency_p95_ms"] == "skipped"
    assert status_map["error_rate"] == "skipped"
    assert status_map["cloud_cost_usd"] == "skipped"
    assert status_map["data_sync_recency_hours"] == "skipped"


@pytest.mark.asyncio
async def test_monitoring_service_records_metrics_file(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    data_sync_metrics = tmp_path / "datasync.json"
    data_sync_metrics.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dry_run": False,
                "bucket": "test-bucket",
                "source_count": 1,
                "sources": ["stub"],
                "result": {
                    "total_raw": 5,
                    "normalized": 5,
                    "written": 5,
                    "skipped": 0,
                    "errors": [],
                },
            }
        ),
        encoding="utf-8",
    )
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=200.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
        MONITORING_METRICS_PATH=str(metrics_path),
        DATA_SYNC_METRICS_PATH=str(data_sync_metrics),
    )
    dispatcher = RecordingDispatcher()
    service = MonitoringService(
        settings,
        app_insights_client=FakeAppInsightsClient(latency_ms=800.0, error_rate=0.01),
        cost_client=FakeCostClient(value=150.0),
        alert_dispatcher=dispatcher,
    )

    alerts = await service.run(dispatch=True)

    assert metrics_path.exists(), "Expected monitoring metrics JSON file to be written."
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert payload["alerts"], "Expected metrics payload to contain alerts."
    metric_names = {alert["metric"] for alert in payload["alerts"]}
    assert metric_names == {"latency_p95_ms", "error_rate", "cloud_cost_usd", "data_sync_recency_hours"}

    status_map = {alert.metric: alert.status for alert in alerts}
    assert status_map == {
        "latency_p95_ms": "ok",
        "error_rate": "ok",
        "cloud_cost_usd": "ok",
        "data_sync_recency_hours": "ok",
    }

    metrics_dir = tmp_path / "metrics_dir"
    fresh_data_sync_dir = tmp_path / "metrics_dir_datasync"
    fresh_data_sync_dir.mkdir()
    data_sync_dir_file = fresh_data_sync_dir / "data_sync_metrics.json"
    data_sync_dir_file.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dry_run": False,
                "bucket": "test-bucket",
                "source_count": 1,
                "sources": ["stub"],
                "result": {
                    "total_raw": 5,
                    "normalized": 5,
                    "written": 5,
                    "skipped": 0,
                    "errors": [],
                },
            }
        ),
        encoding="utf-8",
    )
    dir_settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=200.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
        MONITORING_METRICS_PATH=str(metrics_dir),
        DATA_SYNC_METRICS_PATH=str(fresh_data_sync_dir),
    )
    dir_service = MonitoringService(
        dir_settings,
        app_insights_client=FakeAppInsightsClient(latency_ms=800.0, error_rate=0.01),
        cost_client=FakeCostClient(value=150.0),
        alert_dispatcher=RecordingDispatcher(),
    )

    await dir_service.run(dispatch=False)

    dir_payload_path = metrics_dir / "monitoring_metrics.json"
    assert dir_payload_path.exists()


@pytest.mark.asyncio
async def test_monitoring_service_data_sync_missing_file_alert(tmp_path) -> None:
    missing_path = tmp_path / "missing_metrics.json"
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=0.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.0,
        MONITORING_COST_THRESHOLD_USD=0.0,
        MONITORING_DATA_SYNC_MAX_AGE_HOURS=4.0,
        DATA_SYNC_METRICS_PATH=str(missing_path),
    )
    service = MonitoringService(settings)

    alerts = await service.evaluate()
    status_map = {alert.metric: alert.status for alert in alerts}

    assert status_map["data_sync_recency_hours"] == "alert"
    alert = next(alert for alert in alerts if alert.metric == "data_sync_recency_hours")
    assert "not found" in alert.message


@pytest.mark.asyncio
async def test_monitoring_service_data_sync_detects_dry_run(tmp_path) -> None:
    metrics_path = tmp_path / "data_sync_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dry_run": True,
                "bucket": "test-bucket",
                "source_count": 1,
                "sources": ["stub"],
                "result": {
                    "total_raw": 0,
                    "normalized": 0,
                    "written": 0,
                    "skipped": 0,
                    "errors": [],
                },
            }
        ),
        encoding="utf-8",
    )
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=0.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.0,
        MONITORING_COST_THRESHOLD_USD=0.0,
        MONITORING_DATA_SYNC_MAX_AGE_HOURS=6.0,
        DATA_SYNC_METRICS_PATH=str(metrics_path),
    )
    service = MonitoringService(settings)

    alerts = await service.evaluate()
    alert = next(alert for alert in alerts if alert.metric == "data_sync_recency_hours")
    assert alert.status == "alert"
    assert "dry-run" in alert.message
