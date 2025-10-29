# MindWell Chinese Therapy Bot

MindWell is a Chinese-first digital therapy companion that pairs an empathetic chatbot with a curated network of licensed therapists. The platform blends automated mental health support, longitudinal progress tracking, and human escalation paths tailored for Mandarin-speaking users.

## What’s Included
- **FastAPI backend** (`services/backend`) with modular routers for authentication, chat, therapist discovery, and journey reports.
- **Async persistence layer** powered by SQLAlchemy models for users, therapists, chat sessions/messages, and generated summaries.
- **Seed therapist directory** with database-backed lookups and graceful fallbacks.
- **Terraform infrastructure stubs** (`infra/terraform`) targeting Azure AKS, Azure Postgres, and AWS S3/Bedrock integrations.
- **Design and implementation roadmap** documented in `DEV_PLAN.md` and tracked via `PROGRESS.md`.

## High-Level Architecture
- **Frontend & Mobile (planned):** React Native clients providing chat, therapist discovery, and progress dashboards.
- **Backend API:** FastAPI service orchestrating authentication, chat workflows, therapist recommendations, and summary retrieval.
- **AI Orchestration:** Azure OpenAI as the primary LLM provider, with AWS Bedrock as fallback for resilience (integration pending).
- **Persistence:** Azure Postgres for relational data, S3 buckets for long-form transcripts and generated summaries.
- **Automation Agents:** GitHub Actions runners on EC2, therapist data sync jobs, summary schedulers, and observability monitors (see `AGENTS.md`).

## Running the Backend Locally
```bash
cd services/backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"

# Configure environment variables (see below) then start the API
mindwell-api
```

By default the service listens on `http://0.0.0.0:8000`. Use `/api/docs` for Swagger UI.

### Database Bootstrapping
The API expects a Postgres database reachable via `DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@localhost:5432/mindwell`). On startup the service automatically creates required tables. During early development you can run a local Postgres instance (Docker or Azure Flexible Server).

## Key API Endpoints (Preview)
- `GET /` – service heartbeat with environment metadata.
- `GET /api/healthz` – lightweight health probe.
- `POST /api/auth/sms` – initiate SMS login challenge (stubbed).
- `POST /api/auth/token` – exchange verification code for JWT pair (stubbed).
- `POST /api/chat/message` – persist a chat turn, generate an adaptive placeholder response, and surface therapist suggestions.
- `GET /api/therapists/` – list therapists with optional specialty/language/price filters (DB-backed with seed fallback).
- `GET /api/therapists/{therapist_id}` – fetch therapist detail payload.
- `GET /api/reports/{user_id}` – return the most recent daily and weekly summaries (DB-backed with illustrative fallback).

## Environment Variables
Reference `ENVS.md` for the full catalog. Minimum variables to run the backend locally:
- `APP_ENV`
- `API_PORT`
- `DATABASE_URL`
- `CORS_ALLOW_ORIGINS`

Optional integrations (Azure OpenAI, AWS Bedrock, SMS, Google OAuth, etc.) can be configured as they come online.

## Repository Layout
```
.
├── AGENTS.md                 # Automation responsibilities
├── DEV_PLAN.md               # Product and engineering roadmap
├── ENVS.md                   # Environment variable catalog
├── PROGRESS.md               # Detailed milestone tracking
├── docs/                     # Phase-by-phase design notes
├── infra/terraform/          # Azure + AWS infrastructure definitions
└── services/backend/         # FastAPI backend service
```

## Current Status & Next Steps
See `PROGRESS.md` for an up-to-date checklist. Immediate priorities include:
1. Wiring real SMS and Google OAuth providers into the authentication flow.
2. Connecting chat orchestration to Azure OpenAI with Bedrock fallback and transcript storage in S3.
3. Building scheduled agents for daily/weekly summary generation backed by the new persistence layer.

Contributions should follow the staged plan—update `PROGRESS.md` and relevant docs as features move forward.
