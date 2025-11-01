# MindWell Backend Service

This package scaffolds the core MindWell API platform using FastAPI. It aligns with Phase 3 of the development plan by defining clear module boundaries for authentication, chat orchestration, therapist data, and reporting pipelines.

## Project Layout

```
services/backend/
  app/
    api/         # FastAPI routers grouped by vertical (auth, chat, therapists, reports)
    core/        # Settings, logging, application factory
    models/      # ORM models (placeholder)
    schemas/     # Pydantic schemas shared by endpoints
    services/    # Business logic and integrations (LLM orchestration, storage, etc.)
    main.py      # Entrypoint wiring routers and startup hooks
```

## Quick Start

```bash
cd services/backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
mindwell-api
```

By default the API listens on `http://0.0.0.0:8000`. The current implementation exposes stub endpoints (health, auth, chat, therapists, reports) that illustrate the modular architecture without connecting to external systems yet.

## Database Migrations

The project uses Alembic to manage the PostgreSQL schema. Ensure `DATABASE_URL` is configured (e.g. `postgresql+asyncpg://user:pass@localhost:5432/mindwell`). Then run:

```bash
cd services/backend
alembic upgrade head
```

This command applies the latest migrations, including the bootstrap revision that creates users, therapy, memory, feature flag, and summary tables. The summary scheduler CLI also invokes Alembic via `init_database()` so worker jobs can safely run without manual setup.

## Environment Configuration

Application settings are defined in `app/core/config.py` using `pydantic-settings`. Populate a `.env` file or environment variables for the following fields as they become available:

- `APP_ENV`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `AWS_REGION`
- `S3_SUMMARIES_BUCKET`
- `S3_BUCKET_THERAPISTS`

## Next Steps

- Connect OTP delivery to production SMS providers and replace the Console stub.
- Integrate real Google OAuth exchanges and persist profile metadata securely.
- Harden summary and chat pipelines with structured logging, metrics, and retries.
- Expand automated tests across auth/chat/summaries and wire them into CI Runner.

## Therapist Directory Import

- `TherapistService` supports importing normalized therapist profiles from an S3-compatible bucket via the `/api/therapists/admin/import` endpoint.
- Configure `S3_BUCKET_THERAPISTS` and (optionally) `THERAPIST_DATA_S3_PREFIX` so the Data Sync Agent can publish localized JSON payloads that the backend ingests.
- Use the `dry_run` flag on the import endpoint to preview changes before committing updates to the Postgres store.
- Run the Data Sync agent via `mindwell-data-sync --source path/to/therapists.json --dry-run` to normalize upstream sources and publish `profile_<locale>.json` payloads to the configured bucket.

## Summary Scheduler Agent

- `SummaryGenerationService` (see `app/services/summaries.py`) aggregates recent chat transcripts, calls the LLM orchestrator for structured JSON, and stores daily/weekly summaries in Postgres plus `S3_SUMMARIES_BUCKET`.
- Use the CLI entry point `mindwell-summary-scheduler [daily|weekly|both] --date YYYY-MM-DD` to run schedules or backfill summaries. The command bootstraps the database schema automatically before processing.

## Response Evaluation & Guardrails

- `ResponseEvaluator` (see `app/services/evaluation.py`) applies heuristic checks for empathy, actionable guidance, disclaimers, and high-risk language to score assistant replies.
- `POST /api/evaluations/response` exposes the guardrail check so the Monitoring Agent or CI Runner can gate new prompt templates and regression suites.
- The evaluation response includes normalized metric scores, detected issues with severities, and recommended remediation steps.

## Load Testing

- Locust scenarios live under `loadtests/`. Install Locust (`pip install locust`) and run `locust -f loadtests/locustfile.py --host http://localhost:8000` to exercise chat turns, therapist discovery, and journey report flows.
- Use the headless mode (`--headless -u 50 -r 10 -t 10m`) to integrate throughput checks into CI Runner or Golden Path automation.
