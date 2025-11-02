# Automation & Agent Notes

## CI Runner Agent
- Runs GitHub Actions workloads on EC2-managed runners covering backend, web, and mobile build/test pipelines.
- Assumes cross-account roles via `infra/scripts/assume_ci_role.sh` to publish Docker images and push to AKS.

## Data Sync Agent
- Periodically pulls therapist datasets, normalises entries, and uploads locale-specific JSON payloads to `S3_BUCKET_THERAPISTS`.
- Triggered on a 4-hour cadence; publishes ingestion metrics for Monitoring Agent consumption.

## Summary Scheduler Agent
- Invokes `mindwell-summary-scheduler` to generate daily and weekly conversation summaries.
- Persists outputs to the summaries bucket and backfills gaps when provided an anchor date.

## Monitoring Agent
- Executed via `mindwell-monitoring-agent` on a 5-minute cadence from the observability runner.
- Queries Azure Application Insights for p95 latency and error rate, and AWS Cost Explorer for daily spend.
- Raises alerts when thresholds (`MONITORING_LATENCY_THRESHOLD_MS`, `MONITORING_ERROR_RATE_THRESHOLD`, `MONITORING_COST_THRESHOLD_USD`) are breached.
- Dispatches actionable alerts to the configured webhook (`ALERT_WEBHOOK_URL` / `ALERT_CHANNEL`) after logging structured metrics.
- Supports environment-specific guardrails via `MONITORING_THRESHOLD_OVERRIDES_PATH` and `MONITORING_THRESHOLD_PROFILE`; see `infra/monitoring/threshold_profiles.json` for pilot-ready defaults.
