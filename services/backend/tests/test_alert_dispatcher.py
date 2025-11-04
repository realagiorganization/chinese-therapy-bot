from __future__ import annotations

import pytest

from app.core.config import AppSettings
from app.services.monitoring import AlertDispatcher, MetricAlert


class StubResponse:
    def __init__(self) -> None:
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True


class RecordingClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        self.closed = False

    async def __aenter__(self) -> RecordingClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.closed = True

    async def post(self, url: str, *, json: dict[str, object]) -> StubResponse:
        response = StubResponse()
        self.requests.append({"url": url, "json": json, "response": response})
        return response


class RecordingClientFactory:
    def __init__(self) -> None:
        self.clients: list[RecordingClient] = []

    def __call__(self) -> RecordingClient:
        client = RecordingClient()
        self.clients.append(client)
        return client


@pytest.mark.asyncio
async def test_alert_dispatcher_skips_when_no_actionable_alerts() -> None:
    settings = AppSettings(APP_ENV="qa", ALERT_WEBHOOK_URL="https://hooks.test/alerts")
    factory = RecordingClientFactory()
    dispatcher = AlertDispatcher(settings, http_client_factory=factory)

    alerts = [
        MetricAlert(metric="latency_p95_ms", status="ok", unit="ms", message="Within limits."),
        MetricAlert(metric="error_rate", status="skipped", unit="", message="Not configured."),
    ]

    await dispatcher.dispatch(alerts)

    assert factory.clients == []


@pytest.mark.asyncio
async def test_alert_dispatcher_posts_payload_to_webhook() -> None:
    settings = AppSettings(
        APP_ENV="prod",
        ALERT_WEBHOOK_URL="https://hooks.test/alerts",
        ALERT_CHANNEL="incident-bridge",
    )
    factory = RecordingClientFactory()
    dispatcher = AlertDispatcher(settings, http_client_factory=factory)

    alerts = [
        MetricAlert(
            metric="latency_p95_ms",
            status="alert",
            unit="ms",
            message="P95 latency exceeded.",
            value=2450.0,
            threshold=1800.0,
        ),
        MetricAlert(
            metric="error_rate",
            status="ok",
            unit="",
            message="Error rate within limits.",
            value=0.01,
            threshold=0.05,
        ),
    ]

    await dispatcher.dispatch(alerts)

    assert len(factory.clients) == 1
    client = factory.clients[0]
    assert client.closed is True
    assert len(client.requests) == 1

    request = client.requests[0]
    assert request["url"] == "https://hooks.test/alerts"

    payload = request["json"]
    assert isinstance(payload, dict)
    assert payload["channel"] == "incident-bridge"
    assert "*MindWell Monitoring Alert* — environment `prod`" in payload["text"]
    assert ":rotating_light: `latency_p95_ms` 2450.00ms (threshold 1800.00ms)" in payload["text"]

    response = request["response"]
    assert isinstance(response, StubResponse)
    assert response.raise_for_status_called is True


@pytest.mark.asyncio
async def test_alert_dispatcher_logs_without_webhook_url() -> None:
    settings = AppSettings(APP_ENV="staging")
    factory = RecordingClientFactory()
    dispatcher = AlertDispatcher(settings, http_client_factory=factory)

    alerts = [
        MetricAlert(
            metric="cloud_cost_usd",
            status="alert",
            unit="USD",
            message="Cost threshold exceeded.",
            value=520.0,
            threshold=400.0,
        )
    ]

    await dispatcher.dispatch(alerts)

    assert factory.clients == []
