# Monitoring Guardrails Runbook

This runbook explains how to validate observability guardrails before enabling automated alerts. The workflow covers one-off diagnostics, continuous monitoring, and interpreting the alert payloads.

## Prerequisites
- Backend settings configured with:
  - `APP_INSIGHTS_APP_ID` and `APP_INSIGHTS_API_KEY`
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` **or** IAM role credentials for Cost Explorer
  - `MONITORING_LATENCY_THRESHOLD_MS`, `MONITORING_ERROR_RATE_THRESHOLD`, `MONITORING_COST_THRESHOLD_USD`
  - Optional: `DATA_SYNC_METRICS_PATH` if data freshness checks should read the most recent ingestion report
- Slack/Teams webhook configured via `ALERT_WEBHOOK_URL` (optional for diagnostics, required for automated alerts)
- Local environment has `pip install -e .[dev]` executed from `services/backend/`

## One-off Diagnostic Report
Use the new CLI to run monitoring probes locally without dispatching notifications.

```bash
cd services/backend
poetry run mindwell-monitoring-diagnose --format table --details
```

- Exit code `0`: all metrics `ok` or `skipped`
- Exit code `1`: at least one guardrail breached (status `alert`)
- Exit code `2`: a probe failed to execute (status `error`)
- Add `--allow-alerts` to force exit code `0` even when alerts/errors are present
- Switch to JSON output for scripting:

```bash
poetry run mindwell-monitoring-diagnose --format json > monitoring-report.json
```

## Continuous Agent
When diagnostics look healthy, enable the agent in background mode to run on a 5-minute cadence:

```bash
poetry run mindwell-monitoring-agent
```

Use `--dry-run` to suppress webhook deliveries while validating configuration.

## Interpreting Results
- `latency_p95_ms`: Azure Application Insights percentile over the configured window
- `error_rate`: proportion of failed requests from Application Insights
- `cost_daily_usd`: AWS Cost Explorer unblended cost for the current day
- `data_sync_recency_hours`: Age of the latest therapist data sync metrics file

When `--details` is supplied, the table prints contextual fields (e.g., total requests, Cost Explorer granularity, path to metrics file) to speed up triage.
