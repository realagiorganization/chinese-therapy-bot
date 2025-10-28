# Phase 3 – Backend Service Scaffolding

This document captures the initial FastAPI scaffolding for the MindWell backend service, aligning with the Phase 3 milestones in `PROGRESS.md` and architectural intent in `DEV_PLAN.md`.

## 1. Technology Choices
- **Framework:** FastAPI (Python 3.10+) with async-first design for chat streaming and agent integrations.
- **Packaging:** PEP 621 `pyproject.toml` with optional `dev` extras (`pytest`, `ruff`, `mypy`) to support CI linting and tests.
- **Schema Management:** Pydantic v2 models for request/response validation across auth, chat, therapist, and report flows.
- **Services Layer:** Lightweight domain services encapsulate business logic and integrations, enabling future swapping with real providers (OTP, LLM orchestration, S3, Postgres).

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
| `/api/auth/sms` | POST | Initiates SMS OTP flow (stubbed response). |
| `/api/auth/token` | POST | Exchanges OTP/OAuth code for tokens (fake tokens). |
| `/api/chat/message` | POST | Processes a chat turn, returning placeholder assistant reply. |
| `/api/therapists/` | GET | Lists therapists with filters, backed by static seed data. |
| `/api/therapists/{id}` | GET | Returns therapist detail payload. |
| `/api/reports/{userId}` | GET | Emits example daily/weekly journey reports. |

## 4. Environment & Configuration
- Settings managed via `AppSettings` in `app/core/config.py`.
- Supports overrides for `API_HOST`, `API_PORT`, `APP_ENV`, `CORS_ALLOW_ORIGINS`, storage buckets, and credentials.
- Default CORS policy allows all origins until the frontend domain list is finalized.

## 5. Next Implementation Steps
1. Connect FastAPI dependency graph to actual persistence (PostgreSQL via SQLAlchemy/SQLModel).
2. Integrate Azure AD B2C/OTP provider for production-grade authentication.
3. Plug chat service into Azure OpenAI (primary) and AWS Bedrock (fallback) using structured prompt templates.
4. Replace in-memory therapist data with repository pattern backed by Postgres + S3-sourced i18n profiles.
5. Schedule background tasks for Summary Scheduler and Data Sync agents via Celery, Redis, or Azure Container Apps jobs.
6. Expand automated tests around auth, chat, and reports flows; wire into CI Runner agent pipeline.
