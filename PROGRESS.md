# MindWell Implementation Progress

### Verification Snapshot
- Confirmed referenced Phase 0/1 design artifacts exist under `docs/` (e.g., `docs/phase0_foundations.md`, `docs/phase1_product_design.md`) and align with completed checkboxes.
- Validated Terraform modules for remote state, AKS, observability, and secret management under `infra/terraform/`, matching Phase 2 completed tasks.
- Installed backend dependencies (`pip install .[dev]`) and ran `pytest` to verify the 62-test suite passes after recent service additions (latest run: `pytest`, 62 passed).
- Spot-checked backend services (chat, summaries, feature flags) to ensure the implementations cited in Phase 3 are present and wired into FastAPI dependencies.
- Verified automatic locale detection and therapist profile translation (`services/backend/app/services/language_detection.py`, `services/backend/app/services/translation.py`, `services/backend/app/services/therapists.py`) with client hooks consuming localized payloads (`clients/web/src/hooks/useChatSession.ts`, `clients/mobile/src/screens/ChatScreen.tsx`).
- Revalidated streaming chat fallback now downgrades to a non-streamed turn on SSE drop events (`clients/web/src/hooks/useChatSession.ts`, `services/backend/app/api/routes/chat.py`), eliminating the visible “Stream interrupted” error for transient failures.
- Revalidated streaming chat and guardrail tooling align with Phase 4/5 milestones (`clients/web/src/hooks/useChatSession.ts:1`, `services/backend/app/services/evaluation.py:1`).
- Added regression coverage + FastAPI routing for `/api/chat/stream` and legacy `/therapy/chat/stream` SSE endpoints to close Phase 7 bug tracker item (`services/backend/app/api/routes/chat.py:1`, `services/backend/tests/test_chat_api.py:1`).
- Ensured chat template dataset loads from packaged resources or local fallback, keeping Phase 5 template tooling functional (`services/backend/app/services/templates.py:1`, `services/backend/tests/test_template_service.py:1`).
- Implemented Expo Speech voice playback with adjustable rate/pitch preferences and a disable toggle in the mobile chat experience (`clients/mobile/src/context/VoiceSettingsContext.tsx:1`, `clients/mobile/src/hooks/useVoicePlayback.ts:1`, `clients/mobile/src/screens/ChatScreen.tsx:600`).
- Delivered pilot feedback intake persistence + API to capture pilot cohort sentiment for Phase 6 UAT tracking (`services/backend/app/models/entities.py:381`, `services/backend/app/api/routes/feedback.py:1`, `services/backend/tests/test_feedback_service.py:1`, `services/backend/tests/test_feedback_api.py:1`).
- Confirmed infrastructure automation and CI coverage for mobile clients match Phase 2/7 claims (`infra/terraform/azure_postgres.tf:1`, `.github/workflows/ci.yml:1`).
- README now documents end-to-end frontend/mobile setup workflows as required by DEV_PLAN (`README.md:70`, `README.md:90`).
- Ran `terraform init`/`validate` against `infra/terraform/environments/dev` to remove provider incompatibilities (default node pool mode attribute, AKS SKU tier, dashboard resource deprecation) and generated a reproducible `.terraform.lock.hcl`.
- Hardened AWS Bedrock fallback integration to use `aioboto3.Session().client` and added regression coverage capturing Bedrock + heuristic streaming behavior (`services/backend/app/integrations/llm.py`, `services/backend/tests/test_llm_orchestrator.py`).
- 2025-11-02: Re-audited completed milestones against repository state and updated test counts; no additional discrepancies found.

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
  - [ ] Run `terraform plan`/`apply` for the dev subscription and capture kubeconfig bootstrap steps for CI runners. *(Helper script `infra/scripts/run_terraform_plan.sh`, kubeconfig bootstrap script, and GitHub workflow `.github/workflows/infra-plan.yml` now available; Terraform config validated locally but plan/apply still blocked pending cloud credentials.)*
  - [ ] Validate workload identity/OIDC by deploying a sample pod that fetches a Key Vault secret. *(Validation job scaffolded in `infra/kubernetes/samples/workload-identity-validation.yaml` and documented in `infra/kubernetes/samples/README.md`; run once AKS is provisioned.)*
- [ ] Configure AWS S3 buckets for conversation logs, summaries, and media assets with appropriate IAM roles. *(Buckets + IAM role codified in `infra/terraform/aws_storage.tf`.)*
  - [x] Model cross-cloud AWS VPC, RDS, and automation agent infrastructure to host backend replicas and data sync workloads. *(See `infra/terraform/aws_network.tf`, `infra/terraform/aws_rds.tf`, `infra/terraform/aws_ec2_agents.tf`.)*
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
- [x] Implement oauth2-proxy backed email authentication with session exchange and token quotas.
  - [x] Added demo-code registry with per-code token limits and automated tests covering allowlist validation.
- [x] Implement token issuance with JWT access/refresh tokens, rotation, and token renewal endpoint.
- [x] Replace Google OAuth stub with oauth2-proxy identity headers and email-based account linking.
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
- [x] Implement account onboarding/login flows (oauth2-proxy email + demo codes).
  - [x] Build OTP request/verification UI tied into backend throttling.
  - [x] Document oauth2-proxy header mapping and local fallback behaviour for development.
- [x] Scaffold React Native/Expo mobile client with oauth2-proxy email + demo-code authentication and chat shell. *(see `clients/mobile/` for initial app structure and theming tied to shared tokens.)*
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
- [x] Add RAG pipeline for contextual response generation with conversation snippets and therapist knowledge base. *(chat context prompt now stitches therapist recommendations + memory highlights in `services/backend/app/services/chat.py`)*
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
  - [ ] Recruit pilot cohort, capture structured feedback, and prioritize iteration backlog. *(`PilotFeedback` storage + `/api/feedback/pilot` endpoints now live; cohort recruitment + synthesis still pending.)*
  - [x] Automate pilot feedback synthesis via `/api/feedback/pilot/report` + `mindwell-uat-report` CLI so Markdown/JSON digests feed directly into the backlog review. *(See `services/backend/app/services/feedback.py`, `app/api/routes/feedback.py`, CLI `mindwell-uat-report`, and docs `docs/uat_plan.md` §7.)*

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
  - [x] Instrument product analytics (journey engagement, conversion funnels) and feed into growth roadmap. *(New `analytics_events` schema + service/API/agent: see `services/backend/app/services/analytics.py`, `/api/analytics`, CLI `mindwell-analytics-agent`, and doc `docs/product_analytics.md`.)*

## Phase 8 – Documentation & Launch Readiness
- [x] Complete ENVS.md with environment variable definitions and secure handling notes. *(adds source-of-truth matrix + automation references)*
  - [x] Classify environment variables by mandatory/optional and source-of-truth (Terraform, Key Vault, Secrets Manager). *(see ENVS.md §“Source of Truth & Rotation Overview”)*
  - [x] Document rotation owners and automation hooks for sensitive credentials. *(captured in ENVS.md matrix + `scripts/dump-env-matrix.py`)*
- [x] Update README.md with setup instructions, architecture overview, and usage guide. *(README now covers backend/frontend/mobile quickstart, architecture, observability, and testing expectations.)*
  - [x] Add frontend/mobile setup instructions (illustrative screenshots remain a backlog item).
- [x] Prepare investor/partner summary collateral (optional DOCX/PDF). *(See `docs/investor_partner_brief.md` for investor-ready overview.)*
- [ ] Maintain DEV_PLAN and PROGRESS updates as milestones are achieved.

## Phase 9 – Mobile UI Refinement & Messenger Parity
- [x] Align chat and therapist flows with the Messenger Creation visual target (`Messenger_creation.jpg`) so the mobile shell mirrors the showcased gradients, framing, and typography cadence.
  - [x] Replace inset/pressed button styles with clean outlined variants (white/black/neutral) everywhere in the mobile app per `develop.txt` §1, ensuring hover/disabled tokens stay accessible in both locales.
  - [x] Define keyboard-present layout states: hide the four-tab navigation when the keyboard is up, keep a dedicated top-left back arrow, and validate on iOS/Android simulators.
  - [x] Refresh the palette with lower saturation yellow–green, pink–green, and blue–green options, increase the frosted-glass blur, and implement a bottom-up gradient that fades into beige/off-white mid screen as described in `develop.txt` §§3 & 5.
  - [x] Ship a persistent palette selector inside Settings so QA can toggle the yellow–green / pink–green / blue–green gradients, reusing AsyncStorage and propagating swatch updates through Chat + Therapist screens.
- [x] Enhance the Therapist screen to include AI-personalized recommendations below the search bar.
  - [x] Inject the block “Based on your conversations with the AI, we recommend the following three therapists.” with short rationale strings (A/B/C) before rendering the full card grid. *(Interactive recommendation press targets now focus the matching card and load details per `clients/mobile/src/screens/TherapistDirectoryScreen.tsx`.)*
  - [x] Ensure recommendation copy, therapist badges, and cards visually match the Messenger reference image while supporting Chinese/English text lengths. *(The refreshed block reuses bilingual copy and glass-styled badges with new theme tokens, also in `clients/mobile/src/screens/TherapistDirectoryScreen.tsx`.)*
- [x] Iterate on chrome and typography polish.
  - [x] Brainstorm and document alternative settings button placement options so the icon no longer crowds the top-left corner.
  - [x] Swap headline and body fonts to academic/serious families (e.g., Georgia/Times New Roman inspired) and update style tokens accordingly.
  - [x] Move the voice-mode arrow/icon to the left side of the input, keeping spacing consistent with the Messenger Creation mock.
- [x] Update chat prompt copy to the academic tone from `develop.txt` §9 and surface a psychodynamic quote (choose from §10) below it with localized text + attribution handling.
