# MindWell Chinese Therapy Bot

MindWell is a Chinese-first digital therapy companion that pairs an empathetic chatbot with a curated network of licensed therapists. The platform blends automated mental health support, longitudinal progress tracking, and human escalation paths tailored for Mandarin-speaking users.

## What’s Included
- **FastAPI backend** (`services/backend`) with modular routers for authentication, chat, therapist discovery, and journey reports.
- **Async persistence layer** powered by SQLAlchemy models for users, therapists, chat sessions/messages, and generated summaries.
- **Authentication service** featuring persisted SMS OTP challenges, JWT access/refresh token rotation, and Google OAuth code exchange stubs.
- **Chat orchestration** wired to Azure OpenAI (with AWS Bedrock fallback) and automatic transcript archiving to S3.
- **Seed therapist directory** with database-backed lookups and graceful fallbacks.
- **Conversation memory service** that distills keyword-triggered highlights and exposes them via `/api/memory/{userId}`.
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

### Minimal `.env` Example
Create `services/backend/.env` (or export the variables another way) before running the API:

```bash
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=postgresql+asyncpg://mindwell:mindwell@localhost:5432/mindwell
JWT_SECRET_KEY=change-me-in-production
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com
AZURE_OPENAI_API_KEY=<azure-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AWS_REGION=ap-east-1
S3_CONVERSATION_LOGS_BUCKET=mindwell-conversations-dev
S3_SUMMARIES_BUCKET=mindwell-summaries-dev
SMS_PROVIDER_API_KEY=debug-placeholder
GOOGLE_OAUTH_CLIENT_ID=fake-client
GOOGLE_OAUTH_CLIENT_SECRET=fake-secret
```

For local experiments the SMS provider falls back to console logging and Azure OpenAI calls can be stubbed by omitting the Azure keys (the orchestrator will gracefully degrade to heuristic replies). Review `ENVS.md` for the full catalog of configuration options.

### Database Bootstrapping
The API expects a Postgres database reachable via `DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@localhost:5432/mindwell`). On startup the service automatically creates required tables. During early development you can run a local Postgres instance (Docker or Azure Flexible Server).

## Key API Endpoints (Preview)
- `GET /` – service heartbeat with environment metadata.
- `GET /api/healthz` – lightweight health probe.
- `POST /api/auth/sms` – initiate persisted SMS OTP login challenge.
- `POST /api/auth/token` – exchange OTP or Google authorization code for a JWT/refresh token pair.
- `POST /api/auth/token/refresh` – rotate refresh tokens and mint a fresh access token.
- `POST /api/chat/message` – persist a chat turn, generate an Azure OpenAI (or Bedrock/heuristic) response, archive the transcript to S3, and surface therapist suggestions.
- `GET /api/features/` – inspect feature toggles (merged defaults + database overrides).
- `PUT /api/features/{key}` – create or update a runtime feature switch with optional rollout percentage.
- `POST /api/features/{key}/evaluate` – check if a subject should see an experimental capability.
- `GET /api/therapists/` – list therapists with optional specialty/language/price filters (DB-backed with seed fallback).
- `GET /api/therapists/{therapist_id}` – fetch therapist detail payload.
- `GET /api/reports/{user_id}` – return the most recent daily and weekly summaries (DB-backed with illustrative fallback).
- `GET /api/memory/{user_id}` – retrieve long-lived conversation memories filtered by tracked keywords.

### Authentication Flow
1. **Request OTP** – `POST /api/auth/sms` with the user’s phone number. The server stores a challenge record (5 minute expiry, attempt limits) and logs the OTP through the console provider in development.
2. **Complete login** – `POST /api/auth/token` with `provider=sms`, the received `code`, and the `challenge_id` to obtain JWT + refresh tokens. For Google sign-in, submit the OAuth authorization `code` instead.
3. **Rotate tokens** – `POST /api/auth/token/refresh` with the refresh token to mint a fresh pair; the previous refresh token is revoked to prevent replay.

## Environment Variables
Reference `ENVS.md` for detailed descriptions. Production deployments must at least provide:
- Platform basics: `APP_ENV`, `API_HOST`, `API_PORT`, `CORS_ALLOW_ORIGINS`, `DATABASE_URL`.
- Security & auth: `JWT_SECRET_KEY`, `SMS_PROVIDER_API_KEY`, Google OAuth credentials.
- AI pipeline: Azure OpenAI endpoint/key/deployment (or supply fallback providers).
- Storage: `AWS_REGION`, `S3_CONVERSATION_LOGS_BUCKET`, `S3_SUMMARIES_BUCKET`.

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
1. Executing the Phase 2 Terraform apply and wiring remote state for collaborative infrastructure management.
2. Bootstrapping the shared design system and chat UI for the React Native/web clients (Phase 4).
3. Extending intelligent agent capabilities with therapist recommendations and RAG context injection (Phase 5).

Contributions should follow the staged plan—update `PROGRESS.md` and relevant docs as features move forward.
