from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

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
async def test_monitoring_service_flags_threshold_breaches() -> None:
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=300.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
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

    assert dispatcher.dispatched, "Expected actionable alerts to be dispatched."
    dispatched_metrics = {alert.metric for alert in dispatcher.dispatched[0]}
    assert dispatched_metrics == {"latency_p95_ms", "error_rate", "cloud_cost_usd"}


@pytest.mark.asyncio
async def test_monitoring_service_ok_when_within_thresholds() -> None:
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1800.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.05,
        MONITORING_COST_THRESHOLD_USD=500.0,
        MONITORING_COST_LOOKBACK_DAYS=3,
        AWS_REGION="us-east-1",
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


@pytest.mark.asyncio
async def test_monitoring_service_records_metrics_file(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=200.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
        MONITORING_METRICS_PATH=str(metrics_path),
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
    assert metric_names == {"latency_p95_ms", "error_rate", "cloud_cost_usd"}

    status_map = {alert.metric: alert.status for alert in alerts}
    assert status_map == {
        "latency_p95_ms": "ok",
        "error_rate": "ok",
        "cloud_cost_usd": "ok",
    }

    metrics_dir = tmp_path / "metrics_dir"
    dir_settings = AppSettings(
        APP_ENV="test",
        MONITORING_LATENCY_THRESHOLD_MS=1000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.02,
        MONITORING_COST_THRESHOLD_USD=200.0,
        MONITORING_COST_LOOKBACK_DAYS=1,
        AWS_REGION="us-east-1",
        MONITORING_METRICS_PATH=str(metrics_dir),
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
async def test_monitoring_service_uses_threshold_profile_overrides(tmp_path) -> None:
    overrides = {
        "default": {
            "latency_p95_ms": 1800,
            "error_rate": 0.05,
            "cloud_cost_usd": 450,
            "cost_lookback_days": 2,
        },
        "profiles": {
            "pilot": {
                "latency_p95_ms": 1500,
                "error_rate": 0.04,
                "cloud_cost_usd": 400,
                "cost_lookback_days": 3,
            }
        },
    }
    overrides_path = tmp_path / "monitoring_thresholds.json"
    overrides_path.write_text(json.dumps(overrides), encoding="utf-8")

    settings = AppSettings(
        APP_ENV="pilot",
        MONITORING_LATENCY_THRESHOLD_MS=2000.0,
        MONITORING_ERROR_RATE_THRESHOLD=0.1,
        MONITORING_COST_THRESHOLD_USD=600.0,
        MONITORING_COST_LOOKBACK_DAYS=5,
        MONITORING_THRESHOLD_OVERRIDES_PATH=str(overrides_path),
        MONITORING_THRESHOLD_PROFILE="pilot",
        AWS_REGION="us-east-1",
    )
    service = MonitoringService(
        settings,
        app_insights_client=FakeAppInsightsClient(latency_ms=1600.0, error_rate=0.03),
        cost_client=FakeCostClient(value=420.0),
        alert_dispatcher=RecordingDispatcher(),
    )

    alerts = await service.evaluate()
    status_map = {alert.metric: alert.status for alert in alerts}
    assert status_map["latency_p95_ms"] == "alert"
    assert status_map["error_rate"] == "ok"
    assert status_map["cloud_cost_usd"] == "alert"

    latency_alert = next(alert for alert in alerts if alert.metric == "latency_p95_ms")
    assert latency_alert.details
    assert latency_alert.details["threshold_source"] == "profile"
    assert latency_alert.details["profile"] == "pilot"

    error_alert = next(alert for alert in alerts if alert.metric == "error_rate")
    assert error_alert.details
    assert error_alert.details["threshold_source"] == "profile"
    assert error_alert.details["profile"] == "pilot"

    cost_alert = next(alert for alert in alerts if alert.metric == "cloud_cost_usd")
    assert cost_alert.details
    assert cost_alert.details["lookback_days"] == 3
    assert cost_alert.details["threshold_source"] == "profile"
    assert cost_alert.details["lookback_source"] == "profile"
    assert cost_alert.details["profile"] == "pilot"
