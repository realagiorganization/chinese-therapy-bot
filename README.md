# MindWell Chinese Therapy Bot

MindWell delivers a Chinese-first mental wellness companion that blends an LLM-powered
chat experience with therapist recommendations, journey insights, and automation agents.
This repository contains everything required to run the conversational backend, the
web client, infrastructure-as-code, and the supporting automation services described in
`DEV_PLAN.md`.

## Core Capabilities
- Therapeutic chat assistant backed by Azure OpenAI (with AWS Bedrock/OpenAI fallbacks).
- Persistent conversation history with daily/weekly summaries and keyword memory.
- Therapist discovery directory with recommendation rationales, automatic locale detection, and on-the-fly translation of therapist profiles.
- Journey dashboard surfacing recent insights, highlight cards, and transcript drill-downs.
- Explore modules for breathing exercises, psychoeducation, and dynamic feature rollouts.
- Voice input (browser and server ASR) plus optional text-to-speech playback.
- Email login via oauth2-proxy plus demo-code allowlist with refresh-token rotation and chat-token quotas that surface subscription prompts when credits run out.
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
   > Provide `DEMO_CODE_FILE` for the allowlisted demo codes, configure chat quotas via `CHAT_TOKEN_DEFAULT_QUOTA` / `CHAT_TOKEN_DEMO_QUOTA`, and expose the oauth2-proxy headers using `OAUTH2_PROXY_EMAIL_HEADER`, `OAUTH2_PROXY_USER_HEADER`, and optionally `OAUTH2_PROXY_NAME_HEADER`.
   > The repository ships an active allowlist at `services/backend/config/demo_codes.json` and a template at `demo_codes.sample.json`. Each entry accepts `chat_token_quota` (chat turns before the subscription prompt appears). Every code provisions an isolated `demo` user keyed by the exact string in the file, so demo credits are spent per-code and never bleed into email-based accounts.
3. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
   If this command doesn't work, try to up DB through a container:
   ```bash
   docker run --name mindwell-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=mydb -p 5432:5432 postgres:16
   ```
   And then if the container has exited status:
   ```bash
   docker start mindwell-db
   ```
4. Launch the API:
   ```bash
   mindwell-api
   ```
   The server runs on `http://127.0.0.1:8000` by default; override host/port via `API_HOST` / `API_PORT`.

Agent entry points are exposed as `mindwell-summary-scheduler`, `mindwell-data-sync`,
`mindwell-retention-cleanup`, `mindwell-monitoring-agent`, and `mindwell-analytics-agent`.
Run them within the same virtual environment once credentials are configured. Use
`mindwell-monitoring-agent --dry-run` to verify telemetry access, `mindwell-retention-cleanup`
to enforce S3 transcript/summary retention, and `mindwell-analytics-agent --window-hours 24`
to raise JSON snapshots for the growth team.

### Inspecting registered accounts and chat quotas
There are two ways to reach Azure Postgres and inspect the `users` table:

#### Option A — Azure Cloud Shell (when “Allow Azure Services” is enabled)
1. Launch [shell.azure.com](https://shell.azure.com) (Bash) and fetch `DATABASE_URL`:
   ```bash
   az webapp config appsettings list \
     --resource-group rg-mindwell-dev \
     --name mindwell-dev-api \
     --query "[?name=='DATABASE_URL'].value" -o tsv
   ```
2. Drop the `+asyncpg` suffix and connect from Cloud Shell:
   ```bash
   psql "postgres://USER:PASSWORD@pgflex-mindwell-dev.postgres.database.azure.com:5432/mindwell?sslmode=require"
   ```

#### Option B — from inside the VNet (when the server is locked behind a Private Endpoint)
1. Spin up a VM / Azure Bastion / Container Instance in the same subnet as `pgflex-mindwell-dev`.
2. Install `psql` (`sudo apt install postgresql-client`) and use the same URI:
   ```bash
   psql "postgres://USER:PASSWORD@pgflex-mindwell-dev.postgres.database.azure.com:5432/mindwell?sslmode=require"
   ```
   Private networking keeps the firewall from blocking the connection.

#### Helpful SQL queries
```sql
-- last 50 registered accounts
SELECT id, email, account_type,
       chat_token_quota, chat_tokens_remaining,
       created_at
  FROM users
 ORDER BY created_at DESC
 LIMIT 50;

-- demo users whose quotas hit zero
SELECT email, demo_code,
       chat_token_quota, chat_tokens_remaining
  FROM users
 WHERE account_type = 'demo'
   AND chat_tokens_remaining <= 0;

-- email accounts currently active
SELECT COUNT(*) AS email_accounts
  FROM users
 WHERE account_type = 'email';

-- restore the quota for a specific user
UPDATE users
   SET chat_token_quota = 50,
       chat_tokens_remaining = 50
 WHERE email = 'demo-user@example.com';
```
After running queries, close the session and clear your shell history so the Postgres password doesn’t end up in logs.

### Frontend (Vite/React)
1. Install dependencies:
   ```bash
   cd clients/web
   npm install
   ```
2. Create a `.env.local` (or export) with at minimum:
   ```bash
   # Point email login at the local oauth2-proxy port
   VITE_API_BASE_URL=http://localhost:4180
   ```
   The web client appends `/api` paths internally; point this base URL at the oauth2-proxy-protected MindWell backend.
   Without oauth2-proxy you can temporarily leave `http://localhost:8000`, but only the demo-code login flow will work.
3. Start the dev server with hot module reload:
   ```bash
   npm run dev
   ```
   The server proxies unauthenticated requests to the backend; protected routes still require valid tokens.
   Streaming chat now downgrades to a non-streamed response when the SSE feed drops (the UI listens for `chat_stream_failure` and transparently replays the turn), preventing the “Stream interrupted” banner from appearing on transient network hiccups.
4. Before opening a PR run:
   ```bash
   npm run lint
   npm run test -- --run
   npm run build
   ```
   `npm run preview` serves the production build locally for smoke testing.

### Mobile (Expo)
1. Install dependencies and verify the Expo toolchain:
   ```bash
   cd clients/mobile
   npm install
   npx expo doctor
   ```
   Ensure Xcode (for iOS) or Android Studio/SDK (for Android) are installed before running the native builds.
2. Configure runtime environment variables (read from `app.config.ts`):
   ```bash
   echo "EXPO_PUBLIC_API_BASE_URL=http://localhost:4180" >> .env.local
   echo "EXPO_PUBLIC_SPEECH_REGION=eastasia" >> .env.local
   ```
   Additional keys (speech API credentials, push notification secrets) are documented in `ENVS.md`.
   If oauth2-proxy isn’t running, you can temporarily point to `http://localhost:8000`, but the mobile app will also be confined to demo-only auth.
3. Launch the development server:
   ```bash
   npm run start                # Metro bundler
   npm run ios                  # Requires an iOS simulator / device
   npm run android              # Requires an Android emulator / device
   ```
   The chat composer exposes “press and hold” voice capture; the recorder falls back to server-side ASR when device APIs are unavailable.
4. Performance and asset workflows:
   - `npm run profile:android` assembles a release bundle and outputs timing reports under `clients/mobile/dist/profile-android/`.
   - `npm run optimize:assets` applies Expo image compression; run it after introducing new media.
   - Review `docs/mobile_performance.md` alongside the `useStartupProfiler` logs to track launch latency and gesture responsiveness.

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
- Use `./deploy_azure_database.sh` to provision an Azure PostgreSQL Flexible Server before invoking
  `./deploy_azure_hosting.sh`. The script prints the `DATABASE_URL` (and related variables) that must be exported so
  the hosting deploy can pick up the newly created database.
- Release workflows, semantic versioning, and store checklists are documented in `docs/release_management.md`.

### Publishing Profiles (Azure App Service)
- `publishing_profiles.json` ships as a sanitized template. The `userPWD` field holds the placeholder
  `<<REPLACE_WITH_MINDWELL_PUBLISHING_PROFILE_PASSWORD>>` so no active credentials ever live in git history.
- Export `MINDWELL_PUBLISHING_PROFILE_PASSWORD` with the password downloaded from the Azure Portal (or reset it to rotate credentials):
  ```bash
  export MINDWELL_PUBLISHING_PROFILE_PASSWORD='super-secret-value'
  ```
- Run the helper to materialize a real profile before invoking Azure tooling:
  ```bash
  ./scripts/render_publishing_profile.sh
  # -> writes publishing_profiles.secrets.json (chmod 600, gitignored)
  ```
- Provide `publishing_profiles.secrets.json` to Visual Studio, `az webapp deployment`, or any other tool that expects the raw profile. Remove the generated file once the deployment is complete.

### oauth2-proxy Deployment (Azure App Service)
1. **Build and push the custom image** (oauth2-proxy + Caddy):
   ```bash
   az acr login --name mindwelloauthacr
   docker build -t mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors infra/docker/oauth2-proxy
   docker push mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors
   ```
   The multi-stage Dockerfile runs oauth2-proxy on `127.0.0.1:4181` with Caddy publishing `:4180`, so headers can be added/removed without rebuilding the binary. Use `--oauth-image` if you rely on a different registry.
2. **Prepare the secrets** at `~/.config/mindwell/oauth2-proxy.azure.json`—a JSON object such as `{"KEY":"VALUE"}` with the same keys as `infra/local/oauth2-proxy/.env.oauth2-proxy.example` (see “oauth2-proxy Deployment” in `ENVS.md`). Supply `OAUTH2_PROXY_CLIENT_ID/SECRET`, `OAUTH2_PROXY_COOKIE_SECRET`, `OAUTH2_PROXY_UPSTREAMS`, `OAUTH2_PROXY_CORS_ALLOWED_ORIGINS`, `OAUTH2_PROXY_WHITELIST_DOMAINS`, `OAUTH2_PROXY_ALLOWED_REDIRECT_URLS`, etc.
3. **Deploy the container**:
   ```bash
   ./deploy_azure_hosting.sh --environment dev --resource-group rg-mindwell-dev
   ```
   The script creates/updates `mindwell-<env>-oauth`, sets `WEBSITES_PORT=4180`, and pulls `mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors`. For manual tweaks:
   ```bash
   az webapp config container set \
     --name mindwell-dev-oauth \
     --resource-group rg-mindwell-dev \
     --docker-custom-image-name mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors \
     --docker-registry-server-url https://mindwelloauthacr.azurecr.io \
     --docker-registry-server-user mindwelloauthacr \
     --docker-registry-server-password '<admin-password>'
   az webapp restart --name mindwell-dev-oauth --resource-group rg-mindwell-dev
   ```
4. **Enable CORS and cookies in App Service**:
   ```bash
   az webapp update \
     --name mindwell-dev-oauth \
     --resource-group rg-mindwell-dev \
     --set siteConfig.cors.allowedOrigins='["https://thankful-island-0cf627d00.3.azurestaticapps.net"]' \
           siteConfig.cors.supportCredentials=true
   ```
   Update `allowedOrigins` whenever the SPA hostname changes; otherwise preflight will fail again.
5. **Verify preflight plus primary requests**:
   ```bash
   curl -i -X OPTIONS \
     -H "Origin: https://thankful-island-0cf627d00.3.azurestaticapps.net" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" \
     https://mindwell-dev-oauth.azurewebsites.net/api/auth/demo
   curl -i \
     -H "Origin: https://thankful-island-0cf627d00.3.azurestaticapps.net" \
     "https://mindwell-dev-oauth.azurewebsites.net/oauth2/start?rd=https://thankful-island-0cf627d00.3.azurestaticapps.net/api/auth/demo"
   ```
   Both responses must include `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials: true`.
6. **Local parity**: `infra/local/oauth2-proxy/docker-compose.yml` builds the same image (`docker compose up --build -d`), so the frontend can target `http://localhost:4180`. Additional checks live in `CORS_ACTION_ITEMS.md`.

## Observability & Operations
- Application Insights + Azure Monitor dashboards track latency, error rates, and custom metrics.
- Monitoring Agent raises alerts when thresholds or budget guardrails (defined in Terraform) are breached.
- Configure `APP_INSIGHTS_APP_ID`, `APP_INSIGHTS_API_KEY`, and spend thresholds before scheduling
  `mindwell-monitoring-agent` in production.
- Optionally point `MONITORING_METRICS_PATH` to a writable location so each run emits a JSON snapshot
  (`{"generated_at": "...", "alerts": [...]}`) for downstream ingestion or dashboards.
- S3 versioning and lifecycle policies guard conversation transcripts, summaries, and therapist media.

### Product Analytics
- Backend persists canonical events to `analytics_events` via `POST /api/analytics/events`; clients can supply
  `event_type`, `funnel_stage`, and arbitrary JSON `properties`.
- Aggregate engagement + conversion metrics with `GET /api/analytics/summary?window_hours=24`.
- Automate reporting using `mindwell-analytics-agent --window-hours 168 --output growth/analytics/latest.json`.

## Documentation & Roadmap
- `docs/` contains detailed business, design, and security documentation.
- See `docs/product_analytics.md` for event taxonomy, aggregation workflows, and CLI usage examples.
- `PROGRESS.md` is the canonical source for milestone status; update it as features ship.
- `DEV_PLAN.md` outlines the end-to-end roadmap and should remain authoritative for scope.

## Support & Next Steps
- Implement remaining infrastructure tasks (AKS apply, OIDC validation, AWS bucket provisioning).
- Expand automated test coverage (integration, e2e) and complete compliance workflows.
- Track budget modeling tasks in the new **Cost & Resource Planning** section within `PROGRESS.md`.
- Follow `docs/mobile_performance.md` and `docs/release_management.md` as prerequisites for Phase 4/7 milestones.
