from __future__ import annotations

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
