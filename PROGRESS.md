# MindWell Implementation Progress

### Verification Snapshot
- [x] Recreated backend virtualenv and installed `mindwell-backend` with dev extras to satisfy test dependencies (`pip install -e .[dev]`).
- [x] Ran the backend suite via `pytest`; latest run (2025-11-04T18:57Z) produced 103 passing tests on Python 3.11.14 (historical baselines retained in prior entries for comparison).
- [x] Confirmed referenced Phase 0/1 design artifacts exist under `docs/` (e.g., `docs/phase0_foundations.md`, `docs/phase1_product_design.md`) and align with completed checkboxes.
- [x] Validated Terraform modules for remote state, AKS, observability, and secret management under `infra/terraform/`, matching Phase 2 completed tasks.
- [x] Spot-checked backend services (chat, summaries, feature flags) to ensure the implementations cited in Phase 3 are present and wired into FastAPI dependencies.
- [x] Verified automatic locale detection end-to-end (`services/backend/app/services/language_detection.py:1`, `services/backend/app/services/chat.py:28`, `clients/web/src/hooks/useChatSession.ts:134`, `clients/mobile/src/screens/ChatScreen.tsx:134`), including unit coverage in `services/backend/tests/test_language_detection.py:1`.
- [x] Revalidated streaming chat and guardrail tooling align with Phase 4/5 milestones (`clients/web/src/hooks/useChatSession.ts:1`, `services/backend/app/services/evaluation.py:1`).
- [x] Added regression coverage + FastAPI routing for `/api/chat/stream` and legacy `/therapy/chat/stream` SSE endpoints to close Phase 7 bug tracker item (`services/backend/app/api/routes/chat.py:1`, `services/backend/tests/test_chat_api.py:1`).
- [x] Ensured chat template dataset loads from packaged resources or local fallback, keeping Phase 5 template tooling functional (`services/backend/app/services/templates.py:1`, `services/backend/tests/test_template_service.py:1`).
- [x] Implemented Expo Speech voice playback with adjustable rate/pitch preferences and a disable toggle in the mobile chat experience (`clients/mobile/src/context/VoiceSettingsContext.tsx:1`, `clients/mobile/src/hooks/useVoicePlayback.ts:1`, `clients/mobile/src/screens/ChatScreen.tsx:600`).
- [x] Interrupted ongoing voice playback when the user types, begins recording, or sends a new message so TTS never overlaps with fresh input (`clients/mobile/src/screens/ChatScreen.tsx:624`, `clients/mobile/src/screens/ChatScreen.tsx:651`, `clients/mobile/src/screens/ChatScreen.tsx:716`).
- [x] Added on-device speech recognition fallback so mobile voice capture works when offline (`clients/mobile/src/hooks/useLocalVoiceInput.ts:1`, `clients/mobile/src/hooks/useVoiceInput.ts:1`, `clients/mobile/src/screens/ChatScreen.tsx:140`).
- [x] Delivered pilot feedback intake persistence + API to capture pilot cohort sentiment for Phase 6 UAT tracking (`services/backend/app/models/entities.py:381`, `services/backend/app/api/routes/feedback.py:1`, `services/backend/tests/test_feedback_service.py:1`, `services/backend/tests/test_feedback_api.py:1`).
- [x] Added pilot cohort roster management model, service, API, CLI, and regression tests so recruitment can proceed with structured tracking (`services/backend/app/models/entities.py:414`, `services/backend/app/services/pilot_cohort.py:1`, `services/backend/app/api/routes/pilot_cohort.py:1`, `services/backend/scripts/manage_pilot_cohort.py:1`, `services/backend/tests/test_pilot_cohort_service.py:1`, `services/backend/tests/test_pilot_cohort_api.py:1`).
- [x] Implemented pilot cohort follow-up automation delivering templated outreach recommendations and CLI tooling (`services/backend/app/services/pilot_cohort.py:1`, `services/backend/app/api/routes/pilot_cohort.py:1`, `services/backend/scripts/pilot_followups.py:1`, `services/backend/tests/test_pilot_cohort_service.py:1`, `services/backend/tests/test_pilot_cohort_api.py:1`).
- [x] Added `/api/feedback/pilot/summary` endpoint so product and research can ingest aggregated UAT metrics; validated via the regression suite (`services/backend/app/api/routes/feedback.py:1`, `services/backend/tests/test_feedback_api.py:1`).
- [x] Confirmed infrastructure automation and CI coverage for mobile clients match Phase 2/7 claims (`infra/terraform/azure_postgres.tf:1`, `.github/workflows/ci.yml:1`).
- [x] README documents end-to-end frontend/mobile setup workflows as required by DEV_PLAN (`README.md:70`, `README.md:90`).
- [x] Re-ran `terraform init -backend=false` and `terraform validate` against `infra/terraform` using Terraform 1.6.6 (installed under `.bin/terraform` with a `/usr/local/bin/terraform` symlink); generated updated `.terraform.lock.hcl` pinning azurerm 3.117.1.
- [x] Installed Terraform 1.6.6, Azure CLI 2.79.0, and AWS CLI 2.31.28 into the shared toolchain (now available on `PATH`); re-ran `infra/scripts/check_cloud_prereqs.sh` to confirm binaries are detected and documented the flow still halts pending Azure/AWS credentials.
- [x] 2025-11-06T14:35Z: Re-verified chat streaming + template services and replaced the stubbed RAG claim with a concrete knowledge base pipeline feeding psychoeducation snippets to the LLM and clients (`services/backend/app/services/knowledge_base.py`, `services/backend/tests/test_knowledge_base_service.py`, `clients/web/src/hooks/useChatSession.ts`, `clients/mobile/src/screens/ChatScreen.tsx`).
- [x] 2025-11-05T09:40Z: Audited representative completed milestones (chat streaming endpoints, template service, automation CronJobs, CLI suites) against repository state; confirmed outstanding unchecked items remain blocked on infrastructure credentials or live pilot recruitment.
- [x] Added Kubernetes CronJobs for automation agents (`mindwell-data-sync`, `mindwell-summary-scheduler`, `mindwell-monitoring-agent`) under `infra/kubernetes/agents/` and expanded the shared SecretProviderClass so workloads can pull App Insights, alerting, and AWS credentials from Key Vault.
- [x] Ensured Data Sync agent emits JSON ingestion metrics to `DATA_SYNC_METRICS_PATH`, with CronJob bootstrap logic ensuring directories exist for Monitoring ingestion (`services/backend/app/agents/data_sync.py`, `services/backend/tests/test_data_sync_agent.py`, `infra/kubernetes/agents/cronjob-data-sync.yaml`, `infra/kubernetes/agents/configmap.yaml`).
- [x] Added webhook dispatch regression coverage to guarantee monitoring alerts post actionable payloads (`services/backend/tests/test_alert_dispatcher.py:1`).
- [x] Hardened AWS Bedrock fallback integration to use `aioboto3.Session().client` and added regression coverage capturing Bedrock + heuristic streaming behavior (`services/backend/app/integrations/llm.py`, `services/backend/tests/test_llm_orchestrator.py`).
- [x] 2025-11-03T18:47Z: Re-audited completed milestones against repository state, reran `pytest` (76 passed), and validated Terraform configuration with Terraform 1.6.6 (`terraform init -backend=false` + `terraform validate` via `./.bin/terraform`); no discrepancies found. Follow-up verification 2025-11-04T07:05Z confirmed 92 passing tests with current feature set, and 2025-11-04T18:51Z run verified 101 tests passing after reinstalling dev dependencies and refreshing toolchain binaries. New pilot cohort tooling verified through API + service tests.
- [x] Authored infrastructure preflight script and AKS provisioning runbook to accelerate outstanding Phase 2 apply work (`infra/scripts/check_cloud_prereqs.sh`, `docs/runbooks/aks_provisioning.md`).
- [x] Documented pilot cohort recruitment & UAT execution process to unblock the remaining Phase 6 user testing milestone (`docs/runbooks/pilot_cohort_recruitment.md`).

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
- [ ] Provision Azure AKS cluster, configure node pools, and set up cluster networking. *(Terraform definitions in `infra/terraform/azure_*.tf`; `terraform init`/`validate` succeeded locally on 2025-11-03 using Terraform 1.6.6, but plan/apply still pending cloud credentials.)*
  - [x] Captured end-to-end apply steps and validation checks in `docs/runbooks/aks_provisioning.md`, including kubeconfig bootstrap and workload identity smoke tests.
  - [x] Configure remote Terraform state (Azure Storage/Key Vault) and document backend credentials.
  - [ ] Run `terraform plan`/`apply` for the dev subscription and capture kubeconfig bootstrap steps for CI runners. *(Helper script `infra/scripts/run_terraform_plan.sh`, kubeconfig bootstrap script, and GitHub workflow `.github/workflows/infra-plan.yml` now available; Terraform config validated locally but plan/apply still blocked pending cloud credentials.)*
    - [x] Added `infra/scripts/check_cloud_prereqs.sh` to verify Terraform/Azure/AWS prerequisites before executing plan/apply wrappers.
  - [ ] Validate workload identity/OIDC by deploying a sample pod that fetches a Key Vault secret. *(Validation job scaffolded in `infra/kubernetes/samples/workload-identity-validation.yaml` and documented in `infra/kubernetes/samples/README.md`; run once AKS is provisioned.)*
- [ ] Configure AWS S3 buckets for conversation logs, summaries, and media assets with appropriate IAM roles. *(Buckets + IAM role codified in `infra/terraform/aws_storage.tf`.)*
  - [x] Model cross-cloud AWS VPC, RDS, and automation agent infrastructure to host backend replicas and data sync workloads. *(See `infra/terraform/aws_network.tf`, `infra/terraform/aws_rds.tf`, `infra/terraform/aws_ec2_agents.tf`.)*
  - [ ] Execute Terraform against the target AWS account and capture bucket ARNs plus IAM outputs. *(Terraform validated locally on 2025-11-03; apply awaiting AWS credentials.)*
  - [x] Script CI Runner Agent role assumption (federated login) and document temporary credential retrieval. *(see `infra/scripts/assume_ci_role.sh` + guide `docs/ci_runner_agent.md`)*
  - [x] Define lifecycle rules/prefix conventions for transcripts, summaries, and therapist media ingestion.
- [x] Set up managed database (Azure Postgres or AWS RDS) with schemas for users, therapists, sessions, and reports. *(Azure Flexible Server defined with private networking in `infra/terraform/azure_postgres.tf`; Alembic migrations under `services/backend/alembic/` bootstrap the schema.)*
- [x] Implement secret management (Azure Key Vault + AWS Secrets Manager) and IaC templates (Terraform/Bicep). *(Terraform seeds connection secrets/role assignments in `infra/terraform/azure_keyvault.tf`, rotation SOP in `docs/phase2_secret_management.md`, and backend manifests under `infra/kubernetes/backend/` mount secrets via CSI driver.)*
  - [x] Finalize Terraform outputs/permissions for AKS CSI driver + GitHub OIDC identities.
  - [x] Define secret rotation SOPs and automation hooks for LLM/API credentials.
  - [x] Integrate backend deployment manifests with secret references (Helm/manifest overlays).
  - [x] Automate LLM credential rotation via GitHub Actions workflow `.github/workflows/llm-key-rotation.yml`, leveraging AWS OIDC assume-role, Azure login, and rotation metrics artefacts for audit trails.
  - [x] Extend `mindwell-data-sync` to mirror AWS Secrets Manager entries into Key Vault (`--mirror-secret`), persisting rotation telemetry for Monitoring ingestion.
- [x] Configure observability stack (logging, metrics, alerts) and cost monitoring dashboards. *(App Insights, AKS CPU + error alerts, Azure Portal dashboard, and cost budget alerts codified in `infra/terraform/observability.tf`.)*

## Phase 3 – Backend Services
- [x] Scaffold backend service (FastAPI) with modular architecture. *(see `docs/phase3_backend_scaffold.md` & `services/backend/`)*
- [x] Define SQLAlchemy persistence layer covering users, therapists, chat sessions/messages, and summary tables.
- [x] Integrate async database access for chat, therapist directory, and reports services with graceful seed fallbacks.
- [x] Implement SMS OTP challenge persistence with expiration, throttling, and SMS provider abstraction.
  - [x] Added Twilio-backed SMS provider for production OTP delivery with automated tests covering request/response handling.
- [x] Implement token issuance with JWT access/refresh tokens, rotation, and token renewal endpoint.
- [x] Integrate Google OAuth code verification stub and user identity linking.
- [x] Build chat service for message ingestion, streaming responses, and persistence to database/S3. *(FastAPI endpoint now supports SSE streaming with transcript archival.)*
- [x] Integrate AI model orchestrator (Azure OpenAI primary, AWS Bedrock fallback) with prompt templates.
- [x] Persist chat transcripts and metadata to AWS S3 conversation logs bucket. *(ChatTranscriptStorage now streams per-message JSON events alongside transcript snapshots.)*
- [x] Implement therapist data management APIs (list/get, filtering, admin imports, i18n support). *(FastAPI service now supports locale-aware responses and S3-backed imports via `/api/therapists/admin/import`.)*
  - [x] Extended therapist filters to support price floor/ceiling (`price_min`/`price_max`) with backend validation and test coverage.
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
  - [x] Auto-detect chat locale and surface resolved language across clients. *(LanguageDetector-driven inference in `app/services/chat.py`, SSE propagation parsed in `clients/web/src/api/chat.ts`, and mobile cache hydration in `clients/mobile/src/screens/ChatScreen.tsx`.)*
- [x] Build therapist overview/detail pages with filters and recommendation badges. *(Delivered via `clients/web/src/components/TherapistDirectory.tsx`.)*
  - [x] Port therapist cards to shared design system tokens and integrate live API filters. *(Directory now reuses design-system `Card`/`Button` while filtering through `useTherapistDirectory`.)*
  - [x] Surface recommendation rationales/badges sourced from backend embeddings. *(Recommended therapists render badge styling and show embedding rationale when present.)*
  - [x] Added price range controls (min/max) with i18n placeholders across web/mobile directories to mirror backend filtering.
- [x] Create Journey page showing 10-day daily reports and 10-week weekly reports with drill-down tabs. *(Delivered as `JourneyDashboard` in `clients/web/src/components/JourneyDashboard.tsx`.)*
  - [x] Implement daily/weekly list components backed by reports API.
  - [x] Design detail view with tabbed transcript versus highlights presentation.
  - [x] Ship mobile Journey dashboard with locale-aware summaries, transcript toggles, and refresh support. *(New Expo tab via `clients/mobile/src/screens/JourneyScreen.tsx` + hook/service combo `src/hooks/useJourneyReports.ts` & `src/services/reports.ts`.)*
- [x] Prototype Explore page content modules and personalization hooks.
  - [x] Define placeholder content blocks (breathing exercises, psychoeducation, trending topics).
  - [x] Connect modules to feature flag service for staged rollouts.
- [x] Implement account onboarding/login flows (SMS, Google).
  - [x] Build OTP request/verification UI tied into backend throttling.
  - [x] Add Google OAuth web flow and token exchange using the stub client.
  - [x] Introduced WeChat OAuth stubs end-to-end (FastAPI provider, web/mobile clients) so China-first cohorts can exercise third-party login without real credentials.
- [x] Scaffold React Native/Expo mobile client with SMS + Google authentication and chat shell. *(see `clients/mobile/` for initial app structure and theming tied to shared tokens.)*
- [x] Ship mobile therapist directory with in-app filters and detail view. *(New Expo tab integrates `TherapistDirectoryScreen`, `useTherapistDirectory`, and API-backed detail loading with graceful fallbacks.)*
- [x] Ensure iOS optimization (gesture handling, offline caching, push notifications).
  - [x] Validate React Native/Expo builds against Apple HIG-aligned interactions. *(Checklist captured in `docs/mobile_performance.md` under “Gesture & Interaction Validation”; haptic tab feedback + safe-area banner wiring lives in `clients/mobile/App.tsx:1`, `clients/mobile/src/components/ConnectivityBanner.tsx:1`, with Metro alias support in `clients/mobile/babel.config.js:1`.)*
  - [x] Add offline transcript caching and push notification scaffolding. *(AsyncStorage-backed restoration + Expo Notifications registration in `clients/mobile/src/screens/ChatScreen.tsx`, `src/services/chatCache.ts`, and `src/hooks/usePushNotifications.ts`.)*
  - [x] Delivered safe-area aware composer controls, automatic scroll anchoring, and keyboard offset tuning for notch devices. *(`clients/mobile/src/screens/ChatScreen.tsx:623`.)*
  - [x] Added network-aware banners and voice/send gating with haptic affordances. *(`clients/mobile/src/hooks/useNetworkStatus.ts:1`, `clients/mobile/src/screens/ChatScreen.tsx:439`, `clients/mobile/src/screens/ChatScreen.tsx:667`.)*
- [x] Ensure Android optimization (voice integration parity, performance, compatibility).
  - [x] Ensure voice input parity using Android speech APIs. *(Expo AV recorder + transcription bridge with offline gating in `clients/mobile/src/hooks/useVoiceInput.ts` and composer integration at `clients/mobile/src/screens/ChatScreen.tsx:476`.)*
  - [x] Profile startup/performance on mid-range devices and tune asset sizes. *(Latest profiling workflow and metrics captured in `docs/mobile_performance.md` §“Validation Log – 2025-11-02”; `scripts/mobile-profile-android.sh` baseline artefacts live under `clients/mobile/dist/profile-android/`.)*
  - [x] Reduced ASR workload on Android by defaulting to low-power recording presets while preserving iOS fidelity and improved transcript virtualization. *(`clients/mobile/src/hooks/useVoiceInput.ts:1`; `clients/mobile/src/screens/ChatScreen.tsx:614`.)*

## Phase 5 – Intelligent Agent Features
- [x] Implement conversation memory service with keyword filtering and summarization store. *(see `services/backend/app/services/memory.py` & `/api/memory/{userId}`)*
- [x] Build therapist recommendation engine leveraging embeddings + prompt standardization. *(see `services/backend/app/services/recommendations.py` using Azure/OpenAI embeddings with heuristic fallback + `ChatService` integration)*
- [x] Add RAG pipeline for contextual response generation with conversation memories, therapist knowledge base insights, and psychoeducation snippets. *(Prompt assembly now pulls localized knowledge articles via `services/backend/app/services/knowledge_base.py`, injects them in `services/backend/app/services/chat.py`, and surfaces snippets to web/mobile clients.)*
- [x] Introduce guided chat scene templates for common mental health topics. *(curated dataset in `services/backend/app/data/chat_templates.json`, API `/api/chat/templates`, and web quick-start UI in `clients/web/src/components/ChatPanel.tsx`.)*
- [x] Develop tooling to evaluate model response quality and guardrails. *(Guardrail heuristics + evaluation API via `services/backend/app/services/evaluation.py` and `/api/evaluations/response`.)*

## Phase 6 – Quality Assurance & Compliance
- [x] Create automated testing suites (unit, integration, end-to-end) and load testing scenarios.
  - [x] Expand backend coverage (auth edge cases, streaming chat, S3 persistence). *(pytest suites under `services/backend/tests/` cover AuthService OTP limits, ChatService streaming flow, S3 transcript/summary storage stubs, locale detection in `test_language_detection.py`, and therapist price filter parity in `test_therapist_service.py`.)*
  - [x] Added LLM orchestrator regression tests covering Bedrock fallback handling and streaming heuristics (`services/backend/tests/test_llm_orchestrator.py`).
  - [x] Add summary generation unit tests covering daily pipeline behavior, heuristic fallback, and mood scoring. *(see `services/backend/tests/test_summaries.py`.)*
  - [x] Modernize FastAPI lifespan management and Pydantic settings metadata to eliminate test-time deprecation warnings surfaced by the backend suite.
- [x] Add frontend unit/component tests for chat, therapist flows, and localization. *(Vitest suites in `clients/web/src/App.test.tsx`, `clients/web/src/hooks/__tests__/useTherapistDirectory.test.tsx`, and `clients/web/src/api/therapists.test.ts` validate locale switching, therapist filtering, and API fallback logic.)*
  - [x] Author k6 or Locust load suites for LLM-backed chat throughput. *(Locust scenario under `services/backend/loadtests/` drives chat turns, therapist discovery, and journey report fetches with configurable headless runs.)*
- [x] Conduct security review (OWASP ASVS, data encryption, privacy compliance). *(See `docs/security/owasp_asvs_review.md` for Level 2 assessment, gaps, and mitigation owners.)*
  - [x] Perform threat modeling, dependency scanning, and secret scanning in CI. *(Threat model documented in `docs/threat_model.md` and security checks enforced via `.github/workflows/ci.yml` + `.gitleaks.toml`.)*
  - [x] Validate encryption in transit/at rest across Azure and AWS resources. *(See `docs/security/encryption_validation.md`; S3 buckets enforce TLS + SSE per `infra/terraform/aws_storage.tf` updates.)*
- [x] Implement data governance workflows for PII management and retention.
  - [x] Define retention schedules, anonymization routines, and SAR handling. *(documented in `docs/data_governance.md`)*
  - [x] Automate cleanup of transcripts/summaries per compliance requirements. *(Automated via `mindwell-retention-cleanup` agent in `services/backend/app/agents/retention_cleanup.py` with retention coverage documented in `docs/data_governance.md`.)*
  - [x] Ship SAR CLI tooling and automated tests for export/deletion flows. *(New `DataSubjectService` + CLI scripts under `services/backend/scripts/` with coverage in `services/backend/tests/test_data_subject_service.py`.)*
- [ ] Run user acceptance testing with pilot users and collect feedback for iteration.
  - [x] Draft pilot UAT plan, cohort targets, and success criteria. *(See `docs/uat_plan.md`.)*
  - [x] Instrument structured session logging via `/api/uat/sessions` and the `mindwell-uat-sessions` CLI so facilitators can capture satisfaction, issues, and follow-up actions in real time (`services/backend/app/api/routes/pilot_uat.py`, `services/backend/app/services/pilot_uat.py`, `services/backend/scripts/uat_sessions.py`, `services/backend/tests/test_pilot_uat_service.py`, `services/backend/tests/test_pilot_uat_api.py`).
  - [x] Authored recruitment + UAT execution runbook (`docs/runbooks/pilot_cohort_recruitment.md`) consolidating CLI workflows, reporting cadence, and backlog triage handoffs.
  - [x] Derive prioritized backlog entries from recorded issues/action items via `/api/uat/sessions/backlog`, complete with aggregation tests for service + API layers (`services/backend/app/services/pilot_uat.py`, `services/backend/app/api/routes/pilot_uat.py`, `services/backend/tests/test_pilot_uat_service.py`, `services/backend/tests/test_pilot_uat_api.py`).
  - [x] Added Markdown digest generation to the UAT CLI for quick debrief prep (`scripts/uat_sessions.py`, `tests/test_uat_sessions_cli.py`), enabling facilitation teams to snapshot blockers/highlights before live cohort synthesis.
  - [x] Produced deterministic sample data generator (`services/backend/app/utils/pilot_samples.py`, `services/backend/scripts/generate_pilot_samples.py`, `services/backend/tests/test_pilot_samples.py`) so facilitators can simulate cohorts via `mindwell-pilot-samples` ahead of live UAT.
  - [ ] Recruit pilot cohort, capture structured feedback, and prioritize iteration backlog. *(`PilotFeedback` storage + `/api/feedback/pilot` endpoints now live; `plan_followups` + `mindwell-pilot-followups` automate outreach cadences, while real-world cohort recruitment + synthesis remain outstanding.)*
    - [x] Expose aggregated feedback summary API to feed dashboards and backlog triage (`/api/feedback/pilot/summary`, CLI `summarize_pilot_feedback.py`, regression in `services/backend/tests/test_feedback_api.py`).
    - [x] Build cohort roster management primitives (DB model, service, API, CLI) so Growth/UAT teams can stage recruitment and track status transitions (`services/backend/app/services/pilot_cohort.py`, `/api/pilot-cohort/*`, CLI `mindwell-pilot-cohort`).
    - [x] Generate pilot feedback summary CLI to quantify sentiment/trust scores and tag themes for backlog prioritization. *(Run `mindwell-pilot-feedback-report --format json` to produce metrics.)*
    - [x] Added `mindwell-pilot-cohort summary` command + service metrics to surface consent coverage, status/channel/locale distribution, and tag hotspots for daily recruitment stand-ups (`services/backend/app/services/pilot_cohort.py`, `services/backend/scripts/manage_pilot_cohort.py`, `services/backend/tests/test_pilot_cohort_service.py`).

## Phase 7 – Deployment & Operations
- [x] Finalize CI/CD pipelines for backend, frontend, and mobile releases.
  - [x] Extend GitHub Actions to lint/build/deploy web and mobile clients.
    - [x] Publish release workflow `.github/workflows/release.yml` packaging backend wheels plus web/mobile artefacts (Expo export + Vite dist) with caching + artefact uploads.
    - [x] Add web client lint/test/build job to `.github/workflows/ci.yml` with Node.js caching and Vite build verification.
    - [x] Add mobile client quality gates once React Native project scaffolding is available. *(New `mobile` job in `.github/workflows/ci.yml` runs `npm ci`, lint, and TypeScript checks inside `clients/mobile`.)*
  - [x] Integrate Terraform apply stages with manual approval gates. *(New workflow `.github/workflows/infra-apply.yml` consumes signed plan artifacts and requires environment approval before invoking `infra/scripts/run_terraform_apply.sh`.)*
- [x] Prepare release management process for App Store/TestFlight and Android beta.
  - [x] Document release branching, semantic versioning, and store metadata checklists. *(See `docs/release_management.md` for branching strategy, submission workflows, and platform-specific checklists.)*
  - [x] Provide agent lifecycle controls so on-call engineers can pause/resume automation quickly. *(Updated `scripts/agent-control.sh` manages Summary Scheduler/Data Sync/Retention/Monitoring agents with start/stop/status commands writing logs under `.mindwell/`.)*
- [x] Establish customer support workflows and incident response playbooks.
  - [x] Define escalation matrix, paging channels, and runbook templates. *(Documented in `docs/operations/incident_response.md` tying Monitoring/CIRunner/Data Sync agents into a single escalation process.)*
- [x] Monitor production metrics post-launch and iterate based on telemetry. *(New `MonitoringService` + `mindwell-monitoring-agent` poll Azure App Insights & AWS Cost Explorer with alert dispatch, emit structured JSON snapshots when `MONITORING_METRICS_PATH` is set, and have coverage in `services/backend/tests/test_monitoring_service.py`.)*
  - [x] Added data-sync freshness guardrail so monitoring raises alerts when the Data Sync agent metrics file is stale, missing, or recorded as dry-run/errored (`services/backend/app/services/monitoring.py`, `services/backend/tests/test_monitoring_service.py`).
  - [x] Instrument product analytics (journey engagement, conversion funnels) and feed into growth roadmap. *(New `analytics_events` schema + service/API/agent: see `services/backend/app/services/analytics.py`, `/api/analytics`, CLI `mindwell-analytics-agent`, and doc `docs/product_analytics.md`.)*

## Phase 8 – Documentation & Launch Readiness
- [x] Complete ENVS.md with environment variable definitions and secure handling notes. *(adds source-of-truth matrix + automation references)*
  - [x] Classify environment variables by mandatory/optional and source-of-truth (Terraform, Key Vault, Secrets Manager). *(see ENVS.md §“Source of Truth & Rotation Overview”)*
  - [x] Document rotation owners and automation hooks for sensitive credentials. *(captured in ENVS.md matrix + `scripts/dump-env-matrix.py`)*
- [x] Update README.md with setup instructions, architecture overview, and usage guide. *(README now covers backend/frontend/mobile quickstart, architecture, observability, and testing expectations.)*
  - [x] Add frontend/mobile setup instructions (illustrative screenshots remain a backlog item).
- [x] Prepare investor/partner summary collateral (optional DOCX/PDF). *(See `docs/investor_partner_brief.md` for investor-ready overview.)*
- [x] Maintain DEV_PLAN and PROGRESS updates as milestones are achieved. *(2025-11-03T19:20Z refresh covers local voice input milestone and synced plan documentation.)*
