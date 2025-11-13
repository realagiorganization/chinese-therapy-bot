# Automation & Agent Notes

## Codex CLI Agent
- Всегда отвечает пользователю на русском языке.
- Используется для выполнения локальных задач разработки без выхода в интернет.

## Web Client
- Базовая версия интерфейса, от которой наследуются остальные клиенты.
- Голосовой ввод продолжается до повторного нажатия пользователем кнопки голосового ввода.

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

## Retention Cleanup Agent
- Invoked with `mindwell-retention-cleanup` to enforce transcript/summary retention windows defined in `AppSettings`.
- Supports scoped runs via `--include conversations,summaries`, dry-run previews, and tunable batch sizes for S3 deletes.
- Walks `S3_CONVERSATION_LOGS_BUCKET` and `S3_SUMMARIES_BUCKET`, generating archive/delete counters so compliance can confirm behavior before removal.

## Analytics Agent
- `mindwell-analytics-agent --window-hours 24 --output analytics.json` aggregates the `analytics_events` table via `ProductAnalyticsService`.
- Emits JSON snapshots for growth funnels (active users, conversions, therapist engagement) and optionally saves them for ingestion pipelines.
- Commonly scheduled hourly/daily; if `--output` is omitted the agent prints the payload to stdout for piping into other tools.
