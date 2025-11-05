"""Diagnostic CLI for running monitoring guardrails without dispatching alerts."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from typing import Iterable, Sequence

from app.core.config import get_settings
from app.services.monitoring import MetricAlert, MonitoringService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mindwell-monitoring-diagnose",
        description=(
            "Run MindWell monitoring guardrails once and emit a local report without "
            "triggering alert webhooks."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format for the diagnostic report (default: table).",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Include alert detail payloads in the rendered table output.",
    )
    parser.add_argument(
        "--allow-alerts",
        action="store_true",
        help="Return exit code 0 even when alert/error statuses are present.",
    )
    return parser


def render_table(alerts: Sequence[MetricAlert], *, include_details: bool = False) -> str:
    """Render monitoring alerts in a simple fixed-width table."""
    headers = ("Metric", "Status", "Value", "Threshold", "Unit", "Message")
    rows: list[tuple[str, ...]] = []

    for alert in alerts:
        value_text = _format_number(alert.value)
        threshold_text = _format_number(alert.threshold)
        rows.append(
            (
                alert.metric,
                alert.status,
                value_text,
                threshold_text,
                alert.unit,
                alert.message,
            )
        )
        if include_details and alert.details:
            details_text = _format_details(alert.details)
            rows.append(("", "", "", "", "", f"details: {details_text}"))

    widths: list[int] = []
    for index, header in enumerate(headers):
        candidates = [len(header)]
        candidates.extend(len(row[index]) for row in rows)
        widths.append(max(candidates))

    def format_row(values: Iterable[str]) -> str:
        return "  ".join(value.ljust(width) for value, width in zip(values, widths))

    lines = [format_row(headers)]
    lines.append("  ".join("-" * width for width in widths))
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def _format_number(value: object | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return "-"
        if float(value).is_integer():
            return f"{int(value)}"
        return f"{float(value):.2f}"
    return str(value)


def _format_details(details: dict[str, object]) -> str:
    parts = []
    for key in sorted(details):
        formatted_key = str(key)
        formatted_value = details[key]
        if isinstance(formatted_value, (dict, list)):
            serialized = json.dumps(formatted_value, ensure_ascii=False)
        else:
            serialized = str(formatted_value)
        parts.append(f"{formatted_key}={serialized}")
    return "; ".join(parts) if parts else "(empty)"


def _alerts_to_json(alerts: Sequence[MetricAlert]) -> str:
    payload = [
        {
            "metric": alert.metric,
            "status": alert.status,
            "unit": alert.unit,
            "value": alert.value,
            "threshold": alert.threshold,
            "message": alert.message,
            "details": alert.details,
        }
        for alert in alerts
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _determine_exit_code(alerts: Sequence[MetricAlert]) -> int:
    severity: dict[str, int] = {
        "ok": 0,
        "skipped": 0,
        "alert": 1,
        "error": 2,
    }
    worst = 0
    for alert in alerts:
        worst = max(worst, severity.get(alert.status, 0))
    return worst


async def _run(format_name: str, include_details: bool, allow_alerts: bool) -> int:
    settings = get_settings()
    service = MonitoringService(settings)
    alerts = await service.run(dispatch=False)

    if format_name == "json":
        print(_alerts_to_json(alerts))
    else:
        print(render_table(alerts, include_details=include_details))

    exit_code = 0 if allow_alerts else _determine_exit_code(alerts)
    return exit_code


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = asyncio.run(_run(args.format, args.details, args.allow_alerts))
    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
