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
        self._metrics_path = Path(settings.monitoring_metrics_path) if settings.monitoring_metrics_path else None
        self._threshold_overrides, self._threshold_profile = self._load_threshold_overrides(settings)

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
        return [latency, error_rate, cost]

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

    async def _check_latency(self) -> MetricAlert:
        threshold, threshold_source = self._resolve_threshold(
            "latency_p95_ms", self._settings.monitoring_latency_threshold_ms
        )
        if not self._app_insights_client:
            return MetricAlert(
                metric="latency_p95_ms",
                status="skipped",
                unit="ms",
                threshold=threshold,
                message="Application Insights credentials not configured; skipping latency check.",
                details=self._augment_details({"threshold_source": threshold_source}),
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
                details=self._augment_details({"threshold_source": threshold_source}),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Latency check failed", exc_info=exc)
            return MetricAlert(
                metric="latency_p95_ms",
                status="error",
                unit="ms",
                threshold=threshold,
                message=f"Latency check failed: {exc}",
                details=self._augment_details({"threshold_source": threshold_source}),
            )

    async def _check_error_rate(self) -> MetricAlert:
        threshold, threshold_source = self._resolve_threshold(
            "error_rate", self._settings.monitoring_error_rate_threshold
        )
        if not self._app_insights_client:
            return MetricAlert(
                metric="error_rate",
                status="skipped",
                unit="",
                threshold=threshold,
                message="Application Insights credentials not configured; skipping error rate check.",
                details=self._augment_details({"threshold_source": threshold_source}),
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
                details=self._augment_details({"threshold_source": threshold_source}),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Error rate check failed", exc_info=exc)
            return MetricAlert(
                metric="error_rate",
                status="error",
                unit="",
                threshold=threshold,
                message=f"Error rate check failed: {exc}",
                details=self._augment_details({"threshold_source": threshold_source}),
            )

    async def _check_cost(self) -> MetricAlert:
        threshold, threshold_source = self._resolve_threshold(
            "cloud_cost_usd", self._settings.monitoring_cost_threshold_usd
        )
        lookback_days, lookback_source = self._resolve_int_override(
            "cost_lookback_days", self._settings.monitoring_cost_lookback_days
        )
        lookback_days = max(1, lookback_days)
        if threshold <= 0:
            return MetricAlert(
                metric="cloud_cost_usd",
                status="skipped",
                unit="USD",
                threshold=threshold,
                message="Cost threshold disabled; skipping cost guardrail.",
                details=self._augment_details(
                    {
                        "lookback_days": lookback_days,
                        "threshold_source": threshold_source,
                        "lookback_source": lookback_source,
                    }
                ),
            )
        if not self._cost_client:
            return MetricAlert(
                metric="cloud_cost_usd",
                status="skipped",
                unit="USD",
                threshold=threshold,
                message="AWS Cost Explorer not configured; skipping cost guardrail.",
                details=self._augment_details(
                    {
                        "lookback_days": lookback_days,
                        "threshold_source": threshold_source,
                        "lookback_source": lookback_source,
                    }
                ),
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
                details=self._augment_details(
                    {
                        "lookback_days": lookback_days,
                        "threshold_source": threshold_source,
                        "lookback_source": lookback_source,
                    }
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Cost check failed", exc_info=exc)
            return MetricAlert(
                metric="cloud_cost_usd",
                status="error",
                unit="USD",
                threshold=threshold,
                message=f"Cost check failed: {exc}",
                details=self._augment_details(
                    {
                        "lookback_days": lookback_days,
                        "threshold_source": threshold_source,
                        "lookback_source": lookback_source,
                    }
                ),
            )

    def _load_threshold_overrides(
        self, settings: AppSettings
    ) -> tuple[dict[str, Any], str | None]:
        path = settings.monitoring_threshold_overrides_path
        profile = settings.monitoring_threshold_profile
        if not path:
            return {}, None

        file_path = Path(path)
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning(
                "Monitoring threshold overrides file not found: %s", file_path
            )
            return {}, None
        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to parse monitoring threshold overrides file %s: %s",
                file_path,
                exc,
            )
            return {}, None

        profiles: dict[str, dict[str, Any]] = {}
        if isinstance(payload, dict):
            nested = payload.get("profiles")
            if isinstance(nested, dict):
                profiles.update(
                    {name: value for name, value in nested.items() if isinstance(value, dict)}
                )
            for name, value in payload.items():
                if name == "profiles":
                    continue
                if isinstance(value, dict):
                    profiles[name] = value

            if not profiles and all(not isinstance(v, dict) for v in payload.values()):
                profiles["default"] = {k: v for k, v in payload.items() if isinstance(k, str)}

        if not profiles:
            return {}, None

        selected_name = profile if profile and profile in profiles else None
        if not selected_name and "default" in profiles:
            selected_name = "default"
        if not selected_name:
            selected_name = next(iter(profiles))

        overrides = profiles.get(selected_name, {})
        allowed_keys = {"latency_p95_ms", "error_rate", "cloud_cost_usd", "cost_lookback_days"}
        sanitized = {
            key: overrides[key]
            for key in allowed_keys
            if key in overrides
        }

        if sanitized:
            logger.info(
                "Loaded monitoring threshold overrides profile '%s' from %s",
                selected_name,
                file_path,
            )
            return sanitized, selected_name
        return {}, None

    def _resolve_threshold(self, key: str, fallback: float) -> tuple[float, str]:
        raw = self._threshold_overrides.get(key)
        if raw is None:
            return fallback, "settings"
        try:
            return float(raw), "profile"
        except (TypeError, ValueError):
            logger.debug(
                "Ignoring invalid override for %s: %r (falling back to settings value)",
                key,
                raw,
            )
            return fallback, "settings"

    def _resolve_int_override(self, key: str, fallback: int) -> tuple[int, str]:
        raw = self._threshold_overrides.get(key)
        if raw is None:
            return fallback, "settings"
        try:
            return int(raw), "profile"
        except (TypeError, ValueError):
            logger.debug(
                "Ignoring invalid integer override for %s: %r (falling back to settings value)",
                key,
                raw,
            )
            return fallback, "settings"

    def _augment_details(self, details: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(details)
        if self._threshold_profile:
            enriched["profile"] = self._threshold_profile
        return enriched

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
