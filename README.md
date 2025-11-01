# MindWell Chinese Therapy Bot

MindWell delivers a Chinese-first mental wellness companion that blends an LLM-powered
chat experience with therapist recommendations, journey insights, and automation agents.
This repository contains everything required to run the conversational backend, the
web client, infrastructure-as-code, and the supporting automation services described in
`DEV_PLAN.md`.

## Core Capabilities
- Therapeutic chat assistant backed by Azure OpenAI (with AWS Bedrock/OpenAI fallbacks).
- Persistent conversation history with daily/weekly summaries and keyword memory.
- Therapist discovery directory with recommendation rationales and locale-aware content.
- Journey dashboard surfacing recent insights, highlight cards, and transcript drill-downs.
- Explore modules for breathing exercises, psychoeducation, and dynamic feature rollouts.
- Voice input (browser and server ASR) plus optional text-to-speech playback.
- SMS OTP and Google OAuth login flows with refresh-token rotation.
- Automation agents for data sync, summary scheduling, CI runner orchestration, and monitoring.

## Repository Layout
- `services/backend/` — FastAPI service, domain models, agents, tests, and Alembic migrations.
- `clients/web/` — Vite/React web client with shared design system tokens and i18n bundles.
- `clients/shared/` — Reusable design tokens and assets intended for web/mobile parity.
- `infra/` — Terraform modules for Azure AKS, PostgreSQL, Key Vault, observability, and AWS storage.
- `docs/` — Design foundations, product flows, security guidance, and progression notes.
- `AGENTS.md` — Responsibilities for automation agents operating in production.
- `ENVS.md` — Environment variable reference (mandatory vs optional) for all components.
- `PROGRESS.md` — Implementation tracker mirroring the milestones in `DEV_PLAN.md`.

## Architecture Overview
- **Frontend:** Vite + React 18 application (Chinese-first localization) consuming the FastAPI backend.
- **Backend:** FastAPI service exposing chat, auth, therapist, reports, features, memory, voice, and evaluation routes.
- **Persistence:** Azure Postgres Flexible Server (primary data), AWS S3 buckets for transcripts, summaries, and therapist assets.
- **AI Stack:** Azure OpenAI for chat + embeddings, AWS Bedrock/OpenAI as fallbacks, keyword memory service for context.
- **Automation Agents:**
  - *Data Sync Agent* ingests therapist profiles and uploads normalized payloads to `S3_BUCKET_THERAPISTS`.
  - *Summary Scheduler Agent* produces daily/weekly conversation summaries and persists them to S3.
  - *CI Runner Agent* executes GitHub Actions workflows on EC2 runners for build/test/deploy stages.
  - *Monitoring Agent* enforces latency/error/cost guardrails across observability dashboards.
- **Infrastructure:** Azure AKS (primary deployment target), GitHub OIDC for workload identity, Key Vault & AWS Secrets Manager for secrets.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (or the current LTS)
- PostgreSQL 14+ (local development) or a compatible connection string
- `make`, `git`, and a shell capable of running the provided commands

> Refer to `ENVS.md` for the full list of required environment variables.

### Backend (FastAPI)
1. Create a virtual environment and install dependencies:
   ```bash
   cd services/backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e .[dev]
   ```
2. Configure environment variables (e.g. export locally or use a `.env` file).
3. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
4. Launch the API:
   ```bash
   mindwell-api
   ```
   The server runs on `http://127.0.0.1:8000` by default; override host/port via `API_HOST` / `API_PORT`.

Agent entry points are exposed as `mindwell-summary-scheduler` and `mindwell-data-sync`. Run them within
the same virtual environment once credentials are configured.

### Frontend (Vite/React)
1. Install dependencies and run the dev server:
   ```bash
   cd clients/web
   npm install
   npm run dev
   ```
2. Copy `.env.example` (if present) or export `VITE_API_BASE_URL` to point at the backend (`http://localhost:8000/api` by default). During local development the
   dev server proxies unauthenticated API requests.
3. Run `npm run lint`, `npm run test`, and `npm run build` before submitting changes. Vitest runs in watch mode with `npm run test -- --watch`.

### Mobile (Expo)
1. Install dependencies and launch Metro:
   ```bash
   cd clients/mobile
   npm install
   npm run start
   ```
   Use the Expo Go app or a development build to load the project.
2. Provide `EXPO_PUBLIC_API_BASE_URL`, `EXPO_PUBLIC_SPEECH_REGION`, and authentication secrets via
   `.env` or your preferred secrets manager before running on a device. See `ENVS.md` for the complete list.
3. Voice and gesture validation:
   - The root view now uses `GestureHandlerRootView` so swipe/back gestures match Apple HIG guidance.
   - Hold the microphone button in the chat composer to capture voice input; the app streams audio to
     `/api/voice/transcribe`. Android prompts for microphone permission automatically.
4. Performance tooling:
   - `npm run profile:android` bundles a release build and reports bundle/asset sizes (outputs under `clients/mobile/dist/profile-android`).
   - `npm run optimize:assets` compresses PNG/JPEG assets—run after adding media.
   - `useStartupProfiler` logs startup milestones to device logs; review `docs/mobile_performance.md` for interpretation.

### Voice & Media Services
- Server-side ASR and optional TTS require Azure Cognitive Services credentials:
  - `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, and optionally `AZURE_SPEECH_ENDPOINT`.
- Media uploads default to `S3_MEDIA_BUCKET`; configure lifecycle policies via Terraform.

## Testing & Quality
- **Backend:** `pytest` for unit/integration tests, `ruff` and `mypy` for linting/type checks.
  ```bash
  cd services/backend
  pytest
  ruff check app
  mypy app
  ```
- **Frontend:** `npm run test` (Vitest + Testing Library) and `npm run lint` for ESLint checks.
- **Load Testing:** `services/backend/loadtests/` contains a Locust scenario for exercising chat flows.

## Infrastructure & Deployment
- Terraform modules under `infra/terraform/` manage Azure AKS, PostgreSQL, Key Vault, observability,
  and AWS S3 resources. Run from the repo root with the appropriate cloud credentials.
- Kubernetes manifests/overlays live under `infra/kubernetes/`.
- CI/CD runs on GitHub Actions (self-hosted EC2 runners) executing lint, tests, and deployment stages.
- Azure is the preferred runtime due to available credits; AWS is primarily used for S3 storage and Bedrock fallback.
- Release workflows, semantic versioning, and store checklists are documented in `docs/release_management.md`.

## Observability & Operations
- Application Insights + Azure Monitor dashboards track latency, error rates, and custom metrics.
- Monitoring Agent raises alerts when thresholds or budget guardrails (defined in Terraform) are breached.
- S3 versioning and lifecycle policies guard conversation transcripts, summaries, and therapist media.

## Documentation & Roadmap
- `docs/` contains detailed business, design, and security documentation.
- `PROGRESS.md` is the canonical source for milestone status; update it as features ship.
- `DEV_PLAN.md` outlines the end-to-end roadmap and should remain authoritative for scope.

## Support & Next Steps
- Implement remaining infrastructure tasks (AKS apply, OIDC validation, AWS bucket provisioning).
- Expand automated test coverage (integration, e2e) and complete compliance workflows.
- Track budget modeling tasks in the new **Cost & Resource Planning** section within `PROGRESS.md`.
- Follow `docs/mobile_performance.md` and `docs/release_management.md` as prerequisites for Phase 4/7 milestones.
