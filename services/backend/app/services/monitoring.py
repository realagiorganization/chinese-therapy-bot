from __future__ import annotations

import logging
import math
import re
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence

import aioboto3
import httpx

from app.core.config import AppSettings


logger = logging.getLogger(__name__)


MetricStatus = Literal["ok", "alert", "skipped", "error"]


@dataclass(slots=True)
class MetricAlert:
    """Represents the outcome of a single monitoring probe."""

    metric: str
    status: MetricStatus
    unit: str
    message: str
    value: float | None = None
    threshold: float | None = None
    details: dict[str, Any] | None = None

    @property
    def breached(self) -> bool:
        return self.status == "alert"


class AppInsightsClient:
    """Thin wrapper around the Azure Application Insights query API."""

    def __init__(
        self,
        app_id: str,
        api_key: str,
        *,
        base_url: str = "https://api.applicationinsights.io",
        timeout: float = 10.0,
    ):
        self._app_id = app_id
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)

    async def query(self, kusto_query: str, *, timespan: str = "PT5M") -> dict[str, Any]:
        url = f"{self._base_url}/v1/apps/{self._app_id}/query"
        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "query": kusto_query,
            "timespan": timespan,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


class CostExplorerClient:
    """Queries AWS Cost Explorer for spend analytics."""

    def __init__(self, settings: AppSettings):
        self._region = settings.aws_region or "us-east-1"
        self._session_kwargs: dict[str, Any] = {}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self._session_kwargs["aws_access_key_id"] = settings.aws_access_key_id.get_secret_value()
            self._session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.get_secret_value()

    async def unblended_cost(self, start: date, end: date) -> float:
        """Return total unblended cost between start (inclusive) and end (exclusive)."""
        async with aioboto3.client("ce", region_name=self._region, **self._session_kwargs) as client:
            response = await client.get_cost_and_usage(
                TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )

        total = 0.0
        for result in response.get("ResultsByTime", []):
            amount = (
                result.get("Total", {})
                .get("UnblendedCost", {})
                .get("Amount", "0")
            )
            try:
                total += float(amount)
            except (TypeError, ValueError):
                logger.debug("Skipping cost amount that could not be parsed: %s", amount)
        return total


class AlertDispatcher:
    """Dispatches monitoring alerts to supported sinks (e.g., Slack webhook)."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ):
        self._webhook_url = (
            settings.alert_webhook_url.get_secret_value()
            if settings.alert_webhook_url
            else None
        )
        self._channel = settings.alert_channel
        self._client_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=httpx.Timeout(10.0)))
        self._app_env = settings.app_env

    async def dispatch(self, alerts: Sequence[MetricAlert]) -> None:
        actionable = [alert for alert in alerts if alert.breached]
        if not actionable:
            return

        for alert in actionable:
            logger.warning(
                "Monitoring alert triggered: %s",
                alert.message,
                extra={
                    "metric": alert.metric,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "details": alert.details,
                },
            )

        if not self._webhook_url:
            return

        payload = {
            "text": self._format_message(actionable),
        }
        if self._channel:
            payload["channel"] = self._channel

        async with self._client_factory() as client:
            response = await client.post(self._webhook_url, json=payload)
            response.raise_for_status()

    def _format_message(self, alerts: Iterable[MetricAlert]) -> str:
        lines = [f"*MindWell Monitoring Alert* — environment `{self._app_env}`"]
        for alert in alerts:
            value = f"{alert.value:.2f}" if isinstance(alert.value, float) and not math.isnan(alert.value) else "-"
            threshold = (
                f"{alert.threshold:.2f}" if isinstance(alert.threshold, float) and not math.isnan(alert.threshold) else "-"
            )
            lines.append(
                f":rotating_light: `{alert.metric}` {value}{alert.unit} "
                f"(threshold {threshold}{alert.unit}) — {alert.message}"
            )
        return "\n".join(lines)


class MonitoringService:
    """Polls observability providers and emits alerts when guardrails are violated."""

    _LATENCY_QUERY = """
requests
| where timestamp > ago({window})
| summarize P95DurationMs = percentile(duration, 95)/1ms
"""
    _ERROR_RATE_QUERY = """
requests
| where timestamp > ago({window})
| summarize TotalRequests = sum(itemCount),
          FailedRequests = sumif(itemCount, success == "False" or success == false)
| extend ErrorRate = iif(TotalRequests == 0, 0.0, FailedRequests * 1.0 / TotalRequests)
| project ErrorRate
"""

    def __init__(
        self,
        settings: AppSettings,
        *,
        app_insights_client: AppInsightsClient | None = None,
        cost_client: CostExplorerClient | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ):
        self._settings = settings
        self._app_insights_client = app_insights_client
        if not self._app_insights_client and settings.app_insights_app_id and settings.app_insights_api_key:
            self._app_insights_client = AppInsightsClient(
                settings.app_insights_app_id,
                settings.app_insights_api_key.get_secret_value(),
            )
        self._cost_client = cost_client
        if not self._cost_client and settings.aws_region:
            self._cost_client = CostExplorerClient(settings)
        self._dispatcher = alert_dispatcher or AlertDispatcher(settings)
        self._metrics_path = (
            Path(settings.monitoring_metrics_path).expanduser()
            if settings.monitoring_metrics_path
            else None
        )
        raw_data_sync_path = settings.data_sync_metrics_path
        if raw_data_sync_path:
            path = Path(raw_data_sync_path).expanduser()
            self._data_sync_metrics_path = path if path.suffix else path / "data_sync_metrics.json"
        else:
            self._data_sync_metrics_path = None

    async def run(self, *, dispatch: bool = True) -> list[MetricAlert]:
        alerts = await self.evaluate()
        self._record_metrics(alerts)
        if dispatch:
            await self._dispatcher.dispatch(alerts)
        return alerts

    async def evaluate(self) -> list[MetricAlert]:
        latency = await self._check_latency()
        error_rate = await self._check_error_rate()
        cost = await self._check_cost()
        data_sync = self._check_data_sync()
        return [latency, error_rate, cost, data_sync]

    def _record_metrics(self, alerts: Sequence[MetricAlert]) -> None:
        if not self._metrics_path:
            return

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "alerts": [
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
            ],
        }

        try:
            if self._metrics_path.suffix:
                target_path = self._metrics_path
            else:
                target_path = self._metrics_path / "monitoring_metrics.json"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to persist monitoring metrics: %s", exc, exc_info=exc)

    def _check_data_sync(self) -> MetricAlert:
        threshold = self._settings.monitoring_data_sync_max_age_hours
        metric_name = "data_sync_recency_hours"
        if threshold <= 0:
            return MetricAlert(
                metric=metric_name,
                status="skipped",
                unit="h",
                threshold=threshold,
                message="Data sync freshness guardrail disabled.",
            )

        metrics_path = self._data_sync_metrics_path
        if not metrics_path:
            return MetricAlert(
                metric=metric_name,
                status="skipped",
                unit="h",
                threshold=threshold,
                message="Data sync metrics path not configured; skipping data sync freshness check.",
            )

        if not metrics_path.exists():
            return MetricAlert(
                metric=metric_name,
                status="alert",
                unit="h",
                threshold=threshold,
                message=f"Data sync metrics file not found at {metrics_path}.",
                details={"path": str(metrics_path)},
            )

        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to read data sync metrics from %s", metrics_path, exc_info=exc)
            return MetricAlert(
                metric=metric_name,
                status="error",
                unit="h",
                threshold=threshold,
                message=f"Unable to read data sync metrics: {exc}",
                details={"path": str(metrics_path)},
            )

        generated_raw = payload.get("generated_at")
        try:
            generated_at = self._parse_timestamp(generated_raw)
        except ValueError as exc:
            return MetricAlert(
                metric=metric_name,
                status="error",
                unit="h",
                threshold=threshold,
                message=f"Invalid generated_at in data sync metrics: {exc}",
                details={
                    "path": str(metrics_path),
                    "generated_at": generated_raw,
                },
            )

        now = datetime.now(timezone.utc)
        age_hours = max(0.0, (now - generated_at).total_seconds() / 3600.0)
        result = payload.get("result") or {}
        errors = result.get("errors") or []
        total_raw = result.get("total_raw")
        written = result.get("written")
        dry_run = bool(payload.get("dry_run"))

        total_raw_value = total_raw if isinstance(total_raw, (int, float)) else None
        written_value = written if isinstance(written, (int, float)) else None

        issues: list[str] = []
        if age_hours > threshold:
            issues.append(f"stale ({age_hours:.2f}h > {threshold:.2f}h)")
        if errors:
            issues.append(f"{len(errors)} error(s) reported")
        if (
            not dry_run
            and total_raw_value is not None
            and total_raw_value > 0
            and (written_value is None or written_value == 0)
        ):
            issues.append("no records written")
        if dry_run:
            issues.append("last run executed in dry-run mode")

        status: MetricStatus = "alert" if issues else "ok"
        message = f"Last data sync completed {age_hours:.2f}h ago."
        if issues:
            message += " Issues: " + "; ".join(issues)

        return MetricAlert(
            metric=metric_name,
            status=status,
            unit="h",
            value=age_hours,
            threshold=threshold,
            message=message,
            details={
                "path": str(metrics_path),
                "dry_run": dry_run,
                "total_raw": total_raw,
                "written": written,
                "errors": errors,
            },
        )

    async def _check_latency(self) -> MetricAlert:
        threshold = self._settings.monitoring_latency_threshold_ms
        if not self._app_insights_client:
            return MetricAlert(
                metric="latency_p95_ms",
                status="skipped",
                unit="ms",
                threshold=threshold,
                message="Application Insights credentials not configured; skipping latency check.",
            )

        try:
            result = await self._app_insights_client.query(
                self._LATENCY_QUERY.format(window="5m"),
                timespan="PT5M",
            )
            value = self._extract_single_value(result, "P95DurationMs")
            status: MetricStatus = "alert" if value > threshold else "ok"
            message = f"p95 latency at {value:.0f} ms (threshold {threshold:.0f} ms)."
            return MetricAlert(
                metric="latency_p95_ms",
                status=status,
                unit="ms",
                value=value,
                threshold=threshold,
                message=message,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Latency check failed", exc_info=exc)
            return MetricAlert(
                metric="latency_p95_ms",
                status="error",
                unit="ms",
                threshold=threshold,
                message=f"Latency check failed: {exc}",
            )

    async def _check_error_rate(self) -> MetricAlert:
        threshold = self._settings.monitoring_error_rate_threshold
        if not self._app_insights_client:
            return MetricAlert(
                metric="error_rate",
                status="skipped",
                unit="",
                threshold=threshold,
                message="Application Insights credentials not configured; skipping error rate check.",
            )

        try:
            result = await self._app_insights_client.query(
                self._ERROR_RATE_QUERY.format(window="5m"),
                timespan="PT5M",
            )
            value = self._extract_single_value(result, "ErrorRate")
            status: MetricStatus = "alert" if value > threshold else "ok"
            percentage = value * 100.0
            threshold_pct = threshold * 100.0
            message = f"error rate {percentage:.2f}% (threshold {threshold_pct:.2f}%)."
            return MetricAlert(
                metric="error_rate",
                status=status,
                unit="",
                value=value,
                threshold=threshold,
                message=message,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Error rate check failed", exc_info=exc)
            return MetricAlert(
                metric="error_rate",
                status="error",
                unit="",
                threshold=threshold,
                message=f"Error rate check failed: {exc}",
            )

    async def _check_cost(self) -> MetricAlert:
        threshold = self._settings.monitoring_cost_threshold_usd
        lookback_days = max(1, self._settings.monitoring_cost_lookback_days)
        if threshold <= 0:
            return MetricAlert(
                metric="cloud_cost_usd",
                status="skipped",
                unit="USD",
                threshold=threshold,
                message="Cost threshold disabled; skipping cost guardrail.",
                details={"lookback_days": lookback_days},
            )
        if not self._cost_client:
            return MetricAlert(
                metric="cloud_cost_usd",
                status="skipped",
                unit="USD",
                threshold=threshold,
                message="AWS Cost Explorer not configured; skipping cost guardrail.",
                details={"lookback_days": lookback_days},
            )

        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        # Cost Explorer expects the end date to be exclusive.
        exclusive_end = end_date + timedelta(days=1)

        try:
            value = await self._cost_client.unblended_cost(start=start_date, end=exclusive_end)
            status: MetricStatus = "alert" if value > threshold else "ok"
            message = (
                f"spend over last {lookback_days} day(s): ${value:.2f} "
                f"(threshold ${threshold:.2f})."
            )
            return MetricAlert(
                metric="cloud_cost_usd",
                status=status,
                unit="USD",
                value=value,
                threshold=threshold,
                message=message,
                details={"lookback_days": lookback_days},
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Cost check failed", exc_info=exc)
            return MetricAlert(
                metric="cloud_cost_usd",
                status="error",
                unit="USD",
                threshold=threshold,
                message=f"Cost check failed: {exc}",
                details={"lookback_days": lookback_days},
            )

    def _extract_single_value(self, payload: dict[str, Any], column_name: str) -> float:
        tables = payload.get("tables") or []
        for table in tables:
            columns = table.get("columns") or []
            try:
                column_index = next(
                    index for index, column in enumerate(columns) if column.get("name") == column_name
                )
            except StopIteration:
                continue

            rows = table.get("rows") or []
            if not rows:
                raise ValueError(f"No rows returned for column {column_name}.")

            raw_value = rows[0][column_index]
            return self._parse_numeric(raw_value)

        raise ValueError(f"Unable to locate column '{column_name}' in Application Insights response.")

    def _parse_timestamp(self, raw: str | None) -> datetime:
        if not raw:
            raise ValueError("missing timestamp")
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid ISO8601 timestamp {raw!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    _TIMESPAN_PATTERN = re.compile(
        r"^(?:(?P<days>-?\d+)\.)?(?P<hours>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})(?:\.(?P<fraction>\d+))?$"
    )

    def _parse_numeric(self, raw_value: Any) -> float:
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        if raw_value is None:
            raise ValueError("Metric value is null.")
        if isinstance(raw_value, str):
            stripped = raw_value.strip()
            if not stripped:
                raise ValueError("Metric value is empty.")
            try:
                return float(stripped)
            except ValueError:
                match = self._TIMESPAN_PATTERN.match(stripped)
                if not match:
                    raise ValueError(f"Unsupported metric format: {raw_value}") from None
                days = int(match.group("days") or 0)
                hours = int(match.group("hours"))
                minutes = int(match.group("minutes"))
                seconds = int(match.group("seconds"))
                fraction = match.group("fraction") or "0"
                total_seconds = (
                    days * 86400
                    + hours * 3600
                    + minutes * 60
                    + seconds
                    + float(f"0.{fraction}")
                )
                return total_seconds * 1000.0

        raise ValueError(f"Unsupported metric type: {type(raw_value)!r}")
