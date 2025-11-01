# MindWell Implementation Progress

### Verification Snapshot
- Confirmed referenced Phase 0/1 design artifacts exist under `docs/` (e.g., `docs/phase0_foundations.md`, `docs/phase1_product_design.md`) and align with completed checkboxes.
- Validated Terraform modules for remote state, AKS, observability, and secret management under `infra/terraform/`, matching Phase 2 completed tasks.
- Spot-checked backend services (chat, summaries, feature flags) to ensure the implementations cited in Phase 3 are present and wired into FastAPI dependencies.

## Phase 0 – Foundations
- [x] Review DEV_PLAN.md and existing documentation to align on scope and priorities.
- [x] Define target architecture diagram covering frontend, backend, data, and AI services.
- [x] Select primary cloud deployment target (default Azure AKS) and document rationale.
- [x] Establish project repositories, branching strategy, and CI/CD workflow (GitHub Actions on EC2 runners). *(CI pipeline codified in `.github/workflows/ci.yml` running backend tests & linting.)*

## Phase 1 – Core Product Design
- [x] Document detailed user journeys for chatbot therapy sessions, therapist browsing, and progress tracking. *(see `docs/phase1_product_design.md`)*
- [x] Specify therapist–chatbot integration logic, including recommendation triggers and data flow. *(see `docs/phase1_product_design.md`)*
- [x] Finalize conversation history schema and retention policy (real-time logs, daily snapshots, weekly summaries). *(see `docs/phase1_product_design.md`)*
- [x] Define UX wireframes for chatbot, therapist showcase, Journey reports, and Explore page. *(see `docs/phase1_product_design.md`)*

## Cost & Resource Planning
- [x] Produce detailed Azure/AWS monthly cost breakdown (compute, database, storage, bandwidth) based on Terraform sizing assumptions. *(see `docs/cost_controls.md`)*
- [x] Model Azure OpenAI, Bedrock fallback, and OpenAI usage costs for testing vs. production workloads. *(token forecasts & provider mix captured in `docs/cost_controls.md`)*
- [x] Document Claude Code Mirror licensing plan and budget owner. *(documented in `docs/cost_controls.md`)*
- [x] Publish budget guardrails and alert thresholds for Finance/Monitoring teams in `docs/cost_controls.md`.

## Phase 2 – Platform & Infrastructure Setup
- [ ] Provision Azure AKS cluster, configure node pools, and set up cluster networking. *(Terraform definitions in `infra/terraform/azure_*.tf`; apply pending.)*
  - [x] Configure remote Terraform state (Azure Storage/Key Vault) and document backend credentials.
  - [ ] Run `terraform plan`/`apply` for the dev subscription and capture kubeconfig bootstrap steps for CI runners. *(Helper script `infra/scripts/run_terraform_plan.sh`, kubeconfig bootstrap script, and GitHub workflow `.github/workflows/infra-plan.yml` now available; awaiting secret configuration and first execution.)*
  - [ ] Validate workload identity/OIDC by deploying a sample pod that fetches a Key Vault secret. *(Validation job scaffolded in `infra/kubernetes/samples/workload-identity-validation.yaml` and documented in `infra/kubernetes/samples/README.md`; run once AKS is provisioned.)*
- [ ] Configure AWS S3 buckets for conversation logs, summaries, and media assets with appropriate IAM roles. *(Buckets + IAM role codified in `infra/terraform/aws_storage.tf`.)*
  - [ ] Execute Terraform against the target AWS account and capture bucket ARNs plus IAM outputs.
  - [x] Script CI Runner Agent role assumption (federated login) and document temporary credential retrieval. *(see `infra/scripts/assume_ci_role.sh` + guide `docs/ci_runner_agent.md`)*
  - [x] Define lifecycle rules/prefix conventions for transcripts, summaries, and therapist media ingestion.
- [x] Set up managed database (Azure Postgres or AWS RDS) with schemas for users, therapists, sessions, and reports. *(Azure Flexible Server defined with private networking in `infra/terraform/azure_postgres.tf`; Alembic migrations under `services/backend/alembic/` bootstrap the schema.)*
- [x] Implement secret management (Azure Key Vault + AWS Secrets Manager) and IaC templates (Terraform/Bicep). *(Terraform seeds connection secrets/role assignments in `infra/terraform/azure_keyvault.tf`, rotation SOP in `docs/phase2_secret_management.md`, and backend manifests under `infra/kubernetes/backend/` mount secrets via CSI driver.)*
  - [x] Finalize Terraform outputs/permissions for AKS CSI driver + GitHub OIDC identities.
  - [x] Define secret rotation SOPs and automation hooks for LLM/API credentials.
  - [x] Integrate backend deployment manifests with secret references (Helm/manifest overlays).
- [x] Configure observability stack (logging, metrics, alerts) and cost monitoring dashboards. *(App Insights, AKS CPU + error alerts, Azure Portal dashboard, and cost budget alerts codified in `infra/terraform/observability.tf`.)*

## Phase 3 – Backend Services
- [x] Scaffold backend service (FastAPI) with modular architecture. *(see `docs/phase3_backend_scaffold.md` & `services/backend/`)*
- [x] Define SQLAlchemy persistence layer covering users, therapists, chat sessions/messages, and summary tables.
- [x] Integrate async database access for chat, therapist directory, and reports services with graceful seed fallbacks.
- [x] Implement SMS OTP challenge persistence with expiration, throttling, and SMS provider abstraction.
- [x] Implement token issuance with JWT access/refresh tokens, rotation, and token renewal endpoint.
- [x] Integrate Google OAuth code verification stub and user identity linking.
- [x] Build chat service for message ingestion, streaming responses, and persistence to database/S3. *(FastAPI endpoint now supports SSE streaming with transcript archival.)*
- [x] Integrate AI model orchestrator (Azure OpenAI primary, AWS Bedrock fallback) with prompt templates.
- [x] Persist chat transcripts and metadata to AWS S3 conversation logs bucket. *(ChatTranscriptStorage now streams per-message JSON events alongside transcript snapshots.)*
- [x] Implement therapist data management APIs (list/get, filtering, admin imports, i18n support). *(FastAPI service now supports locale-aware responses and S3-backed imports via `/api/therapists/admin/import`.)*
- [x] Deliver Data Sync agent to normalize therapist sources and publish S3 payloads. *(CLI `mindwell-data-sync` under `services/backend/app/agents/data_sync.py` produces `profile_<locale>.json` artifacts for ingestion.)*
- [x] Develop summary generation pipeline (daily & weekly) with scheduled workers and storage integration. *(see `services/backend/app/services/summaries.py` & `app/agents/summary_scheduler.py`)*
- [x] Expose journey report APIs delivering recent summaries and chat history slices. *(Journey endpoint returns daily/weekly digests plus recent conversation slices via `ReportsService`.)*
- [x] Add feature flags/configuration service to toggle experimental capabilities. *(FeatureFlagService with `/api/features` router enables runtime toggles + percentage rollouts backed by Postgres.)*

## Phase 4 – Frontend & Mobile Clients
- [x] Set up shared design system and localization framework (Chinese-first). *(shared tokens under `clients/shared/design-tokens/`, new fallback-aware i18n config, and guidelines in `docs/design_system_guidelines.md`.)*
  - [x] Publish reusable component tokens (buttons, typography, colors) for web and mobile parity.
  - [x] Expand locale bundle management and fallback strategy (zh-CN primary, en-US secondary, zh-TW placeholder).
  - [x] Document theming usage guidelines for React web/Native clients.
- [x] Implement chatbot screen with streaming UI, voice input (local + server ASR), and TTS playback controls. *(Web client now streams via `useChatSession`, supports Web Speech + server ASR fallback, and retains auto TTS toggles.)*
  - [x] Build web chat hook handling SSE turn streaming with graceful JSON fallback. *(Implemented via `clients/web/src/hooks/useChatSession.ts` + `api/chat.ts` SSE parser.)*
  - [x] Surface therapist recommendations and memory highlights inline with the transcript. *(Rendered in `clients/web/src/components/ChatPanel.tsx` alongside each turn.)*
  - [x] Wire Web Speech API voice capture and speech synthesis toggles with server ASR handoff hooks. *(Azure-backed `/api/voice/transcribe` endpoint + `useServerTranscriber` enable server recording fallback with shared error handling.)*
- [x] Build therapist overview/detail pages with filters and recommendation badges. *(Delivered via `clients/web/src/components/TherapistDirectory.tsx`.)*
  - [x] Port therapist cards to shared design system tokens and integrate live API filters. *(Directory now reuses design-system `Card`/`Button` while filtering through `useTherapistDirectory`.)*
  - [x] Surface recommendation rationales/badges sourced from backend embeddings. *(Recommended therapists render badge styling and show embedding rationale when present.)*
- [x] Create Journey page showing 10-day daily reports and 10-week weekly reports with drill-down tabs. *(Delivered as `JourneyDashboard` in `clients/web/src/components/JourneyDashboard.tsx`.)*
  - [x] Implement daily/weekly list components backed by reports API.
  - [x] Design detail view with tabbed transcript versus highlights presentation.
- [x] Prototype Explore page content modules and personalization hooks.
  - [x] Define placeholder content blocks (breathing exercises, psychoeducation, trending topics).
  - [x] Connect modules to feature flag service for staged rollouts.
- [x] Implement account onboarding/login flows (SMS, Google).
  - [x] Build OTP request/verification UI tied into backend throttling.
  - [x] Add Google OAuth web flow and token exchange using the stub client.
- [x] Scaffold React Native/Expo mobile client with SMS + Google authentication and chat shell. *(see `clients/mobile/` for initial app structure and theming tied to shared tokens.)*
- [ ] Ensure iOS optimization (gesture handling, offline caching, push notifications).
  - [ ] Validate React Native/Expo builds against Apple HIG-aligned interactions.
  - [x] Add offline transcript caching and push notification scaffolding. *(AsyncStorage-backed restoration + Expo Notifications registration in `clients/mobile/src/screens/ChatScreen.tsx`, `src/services/chatCache.ts`, and `src/hooks/usePushNotifications.ts`.)*
- [ ] Ensure Android optimization (voice integration parity, performance, compatibility).
  - [ ] Ensure voice input parity using Android speech APIs.
  - [ ] Profile startup/performance on mid-range devices and tune asset sizes.

## Phase 5 – Intelligent Agent Features
- [x] Implement conversation memory service with keyword filtering and summarization store. *(see `services/backend/app/services/memory.py` & `/api/memory/{userId}`)*
- [x] Build therapist recommendation engine leveraging embeddings + prompt standardization. *(see `services/backend/app/services/recommendations.py` using Azure/OpenAI embeddings with heuristic fallback + `ChatService` integration)*
- [x] Add RAG pipeline for contextual response generation with conversation snippets and therapist knowledge base. *(chat context prompt now stitches therapist recommendations + memory highlights in `services/backend/app/services/chat.py`)*
- [x] Introduce guided chat scene templates for common mental health topics. *(curated dataset in `services/backend/app/data/chat_templates.json`, API `/api/chat/templates`, and web quick-start UI in `clients/web/src/components/ChatPanel.tsx`.)*
- [x] Develop tooling to evaluate model response quality and guardrails. *(Guardrail heuristics + evaluation API via `services/backend/app/services/evaluation.py` and `/api/evaluations/response`.)*

## Phase 6 – Quality Assurance & Compliance
- [ ] Create automated testing suites (unit, integration, end-to-end) and load testing scenarios.
  - [x] Expand backend coverage (auth edge cases, streaming chat, S3 persistence). *(new pytest suites under `services/backend/tests/` cover AuthService OTP limits, ChatService streaming flow, and S3 transcript/summary storage stubs.)*
  - [x] Add summary generation unit tests covering daily pipeline behavior, heuristic fallback, and mood scoring. *(see `services/backend/tests/test_summaries.py`.)*
- [x] Add frontend unit/component tests for chat, therapist flows, and localization. *(Vitest suites in `clients/web/src/App.test.tsx`, `clients/web/src/hooks/__tests__/useTherapistDirectory.test.tsx`, and `clients/web/src/api/therapists.test.ts` validate locale switching, therapist filtering, and API fallback logic.)*
  - [x] Author k6 or Locust load suites for LLM-backed chat throughput. *(Locust scenario under `services/backend/loadtests/` drives chat turns, therapist discovery, and journey report fetches with configurable headless runs.)*
- [ ] Conduct security review (OWASP ASVS, data encryption, privacy compliance).
  - [x] Perform threat modeling, dependency scanning, and secret scanning in CI. *(Threat model documented in `docs/threat_model.md` and security checks enforced via `.github/workflows/ci.yml` + `.gitleaks.toml`.)*
  - [ ] Validate encryption in transit/at rest across Azure and AWS resources.
- [ ] Implement data governance workflows for PII management and retention.
  - [x] Define retention schedules, anonymization routines, and SAR handling. *(documented in `docs/data_governance.md`)*
  - [x] Automate cleanup of transcripts/summaries per compliance requirements. *(Automated via `mindwell-retention-cleanup` agent in `services/backend/app/agents/retention_cleanup.py` with retention coverage documented in `docs/data_governance.md`.)*
- [ ] Run user acceptance testing with pilot users and collect feedback for iteration.
  - [ ] Recruit pilot cohort, capture structured feedback, and prioritize iteration backlog.

## Phase 7 – Deployment & Operations
- [ ] Finalize CI/CD pipelines for backend, frontend, and mobile releases.
  - [ ] Extend GitHub Actions to lint/build/deploy web and mobile clients.
    - [x] Add web client lint/test/build job to `.github/workflows/ci.yml` with Node.js caching and Vite build verification.
    - [x] Add mobile client quality gates once React Native project scaffolding is available. *(New `mobile` job in `.github/workflows/ci.yml` runs `npm ci`, lint, and TypeScript checks inside `clients/mobile`.)*
  - [ ] Integrate Terraform apply stages with manual approval gates.
- [ ] Prepare release management process for App Store/TestFlight and Android beta.
  - [ ] Document release branching, semantic versioning, and store metadata checklists.
- [ ] Establish customer support workflows and incident response playbooks.
  - [ ] Define escalation matrix, paging channels, and runbook templates.
- [ ] Monitor production metrics post-launch and iterate based on telemetry.
  - [ ] Instrument product analytics (journey engagement, conversion funnels) and feed into growth roadmap.

## Phase 8 – Documentation & Launch Readiness
- [x] Complete ENVS.md with environment variable definitions and secure handling notes. *(adds source-of-truth matrix + automation references)*
  - [x] Classify environment variables by mandatory/optional and source-of-truth (Terraform, Key Vault, Secrets Manager). *(see ENVS.md §“Source of Truth & Rotation Overview”)*
  - [x] Document rotation owners and automation hooks for sensitive credentials. *(captured in ENVS.md matrix + `scripts/dump-env-matrix.py`)*
- [ ] Update README.md with setup instructions, architecture overview, and usage guide.
  - [ ] Add frontend/mobile setup instructions and illustrative screenshots once available.
- [ ] Prepare investor/partner summary collateral (optional DOCX/PDF).
- [ ] Maintain DEV_PLAN and PROGRESS updates as milestones are achieved.
