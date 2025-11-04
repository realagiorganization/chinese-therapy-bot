# Phase 3 – Backend Service Scaffolding

This document captures the initial FastAPI scaffolding for the MindWell backend service, aligning with the Phase 3 milestones in `PROGRESS.md` and architectural intent in `DEV_PLAN.md`.

## 1. Technology Choices
- **Framework:** FastAPI (Python 3.10+) with async-first design for chat streaming and agent integrations.
- **Packaging:** PEP 621 `pyproject.toml` with optional `dev` extras (`pytest`, `ruff`, `mypy`) to support CI linting and tests.
- **Schema Management:** Pydantic v2 models for request/response validation across auth, chat, therapist, and report flows.
- **Services Layer:** Lightweight domain services encapsulate business logic and integrations, enabling future swapping with real providers (identity proxy, LLM orchestration, S3, Postgres).

## 2. Project Layout (`services/backend`)

```
services/backend/
  app/
    api/               # FastAPI router registration and dependencies
    core/              # App factory + settings management
    schemas/           # Pydantic models grouped by domain
    services/          # Business logic stubs per domain
    models/            # Placeholder for SQLAlchemy entities
    main.py            # mindwell-api entrypoint (uvicorn wrapper)
  pyproject.toml       # Project metadata and dependencies
  README.md            # Usage instructions and roadmap
```

## 3. Available Endpoints (Stubbed)
| Path | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Root informational heartbeat with environment metadata. |
| `/api/healthz` | GET | Liveness probe. |
| `/api/auth/session` | POST | Exchanges oauth2-proxy identity headers for MindWell token pairs. |
| `/api/auth/demo` | POST | Validates allowlisted demo codes and issues token pairs. |
| `/api/auth/token/refresh` | POST | Rotates refresh tokens; revokes the prior token instance. |
| `/api/chat/message` | POST | Processes a chat turn; streams assistant tokens via SSE when `enable_streaming` is true, otherwise returns the full reply payload. |
| `/api/chat/templates` | GET | Returns curated conversation templates (per locale/topic) with sample openings and self-care nudges. |
| `/api/therapists/` | GET | Lists therapists with filters, backed by static seed data. |
| `/api/therapists/{id}` | GET | Returns therapist detail payload. |
| `/api/reports/{userId}` | GET | Returns latest daily/weekly journey reports plus recent conversation slices for context. |
| `/api/memory/{userId}` | GET | Returns keyword-filtered conversation memories to power long-lived context. |
| `/api/evaluations/response` | POST | Scores an assistant reply for empathy, actionability, disclaimers, and guardrail violations. |

### 3.1 Streaming Response Contract
- The chat endpoint emits **Server-Sent Events (SSE)** when `enable_streaming=true` in the request body.
- Event order: `session_established` (session metadata + therapist IDs) → repeated `token` events (delta text) → terminal `complete` event with the persisted assistant message.
- Clients that prefer non-streaming behaviour can set `enable_streaming=false` and receive the legacy JSON `ChatResponse`.

## 4. Environment & Configuration
- Settings managed via `AppSettings` in `app/core/config.py`.
- Supports overrides for `API_HOST`, `API_PORT`, `APP_ENV`, `CORS_ALLOW_ORIGINS`, storage buckets, and credentials.
- Default CORS policy allows all origins until the frontend domain list is finalized.

## 5. Next Implementation Steps
1. Connect FastAPI dependency graph to actual persistence (PostgreSQL via SQLAlchemy/SQLModel).
2. Harden oauth2-proxy integration for production (signed cookies, header pinning, token quotas).
3. Plug chat service into Azure OpenAI (primary) and AWS Bedrock (fallback) using structured prompt templates.
4. Replace in-memory therapist data with repository pattern backed by Postgres + S3-sourced i18n profiles.
5. Schedule background tasks for Summary Scheduler and Data Sync agents via Celery, Redis, or Azure Container Apps jobs.
6. Expand automated tests around auth, chat, and reports flows; wire into CI Runner agent pipeline.

## 6. Therapist Data Management

- `TherapistService` now incorporates locale-aware lookups, enriched availability metadata, and a persistence model for localized profiles.
- `/api/therapists/admin/import` enables administrators or automation agents to ingest normalized therapist JSON payloads from `S3_BUCKET_THERAPISTS`, honoring `THERAPIST_DATA_S3_PREFIX` and optional locale filters.
- The service can run in dry-run mode to preview changes without mutating the database, returning counts of created, updated, and unchanged records.

## 7. Summary Generation Pipeline

- `SummaryGenerationService` collates recent chat transcripts, calls the AI orchestrator for JSON-formatted daily/weekly digests, and persists results to Postgres plus the `S3_SUMMARIES_BUCKET`.
- Keyword-driven heuristics provide resilient fallbacks when LLM providers are unavailable, ensuring the Summary Scheduler Agent still produces output.
- The CLI entry point `mindwell-summary-scheduler` (see `app/agents/summary_scheduler.py`) powers automation jobs:

```bash
# Generate daily summaries for today
mindwell-summary-scheduler

# Generate both daily and weekly summaries anchored to a specific date
mindwell-summary-scheduler both --date 2025-01-15
```

## 8. Journey Reports API

- `ReportsService` queries stored summaries and recent chat sessions (up to 3 sessions × 20 messages) to surface contextual conversation slices alongside daily and weekly aggregates.
- `/api/reports/{userId}` now returns `conversations` in addition to `daily` and `weekly` payloads, enabling Journey surfaces to render recency-aware chat excerpts.

## 9. Guardrail Evaluation Service

- `ResponseEvaluator` (see `app/services/evaluation.py`) implements heuristic guardrails for high-risk language, medical claims, empathetic tone, and actionable guidance.
- The endpoint `/api/evaluations/response` provides machine-readable scoring so CI pipelines and agents can block unsafe template changes or flag sessions for human review.
