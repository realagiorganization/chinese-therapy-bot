from __future__ import annotations

import json
from typing import Sequence

import pytest

from app.services.monitoring import MetricAlert
from scripts.monitoring_diagnose import (
    main,
    render_table,
)


def _sample_alerts() -> list[MetricAlert]:
    return [
        MetricAlert(
            metric="latency_p95_ms",
            status="ok",
            unit="ms",
            value=120.0,
            threshold=500.0,
            message="Latency within threshold.",
            details={"window": "PT5M"},
        ),
        MetricAlert(
            metric="error_rate",
            status="alert",
            unit="%",
            value=7.2,
            threshold=5.0,
            message="Error rate above SLO.",
            details={"total_requests": 250, "failed_requests": 18},
        ),
    ]


def test_render_table_includes_details() -> None:
    output = render_table(_sample_alerts(), include_details=True)
    assert "latency_p95_ms" in output
    assert "details: failed_requests=18; total_requests=250" in output
    assert "error_rate" in output
    assert "alert" in output


def test_main_table_output_sets_exit_code(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    alerts = _sample_alerts()

    class FakeMonitoringService:
        def __init__(self, _settings: object) -> None:
            pass

        async def run(self, dispatch: bool = True) -> Sequence[MetricAlert]:
            assert dispatch is False
            return alerts

    monkeypatch.setattr("scripts.monitoring_diagnose.get_settings", lambda: object())
    monkeypatch.setattr("scripts.monitoring_diagnose.MonitoringService", FakeMonitoringService)

    with pytest.raises(SystemExit) as exc:
        main(["--format", "table"])

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "latency_p95_ms" in captured.out
    assert "error_rate" in captured.out


def test_main_json_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    alerts = [
        MetricAlert(
            metric="cost_daily_usd",
            status="ok",
            unit="USD",
            value=42.5,
            threshold=100.0,
            message="Spend within budget.",
            details={},
        ),
    ]

    class FakeMonitoringService:
        def __init__(self, _settings: object) -> None:
            pass

        async def run(self, dispatch: bool = True) -> Sequence[MetricAlert]:
            assert dispatch is False
            return alerts

    monkeypatch.setattr("scripts.monitoring_diagnose.get_settings", lambda: object())
    monkeypatch.setattr("scripts.monitoring_diagnose.MonitoringService", FakeMonitoringService)

    with pytest.raises(SystemExit) as exc:
        main(["--format", "json"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == [
        {
            "metric": "cost_daily_usd",
            "status": "ok",
            "unit": "USD",
            "value": 42.5,
            "threshold": 100.0,
            "message": "Spend within budget.",
            "details": {},
        }
    ]
