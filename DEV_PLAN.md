---

# **MindWell Development Plan**

## **1. App Flow and User Scenario Design**

### **a. Main User Scenarios**

**Status:** Completed — see `docs/phase1_product_design.md` for detailed user journeys, data flow diagrams, and retention policy references.

| **Priority** | **Task Description** |
| --- | --- |
| High | **Chatbot–Therapist Integration:** Define the logic connecting chatbot responses with therapist recommendations. |
| High | **Therapist Display Interface:** Determine what content is shown on the therapist profile or showcase page. |
| High | **Conversation History Management:** Design how past sessions, chat summaries, and psychological state analyses are displayed and managed. |

### **b. Chat Experience Optimization**

**Status:** Implemented — template-driven chat scenes, response evaluation heuristics, and conversation memory are live with regression coverage.

| **Priority** | **Task Description** |
| --- | --- |
| Medium / Long-term | **Chat Scene Design:** 1. Template-based Q&A for common mental health topics. 2. Model response quality evaluation. |
| Medium | **Model Memory:** Implement keyword-based filtering for selective conversation storage and summary generation. |

---

## **2. Cost Estimate**

**Status:** Completed — financial modeling captured in `docs/cost_controls.md` with guardrails mirrored in monitoring alerts.

### **Infrastructure (Approx. USD 162/month)**

| **Item** | **Cost** |
| --- | --- |
| Compute Resources | $100/month |
| Database & Cache | $60/month |
| Domain (.com) | $13/year and up |

### **Model Usage**

| **Stage** | **Input** | **Output** | **Unit** |
| --- | --- | --- | --- |
| Testing Phase | $0.5 | $1.5 | per 1M tokens |
| Production Phase | $3 | $15 | per 1M tokens |
| **Estimated input-output ratio:** 1:2 |  |  |  |

### **AI Coding Tools**

- Claude Code Mirror: ¥162/month

---

## **3. Development Timeline (Rankang)**

**Status:** Tracking — Weeks 1–4 scope shipped (chat core, auth, therapist management). Release processes for Weeks 5–7 documented in `docs/release_management.md` and `docs/changelog.md` now seeds cadence notes.

| **Week** | **Milestone** | **Details** |
| --- | --- | --- |
| Weeks 1–4 | **Core Scene Development** | - Model Integration - Account Management (SMS login, Google/third-party login) - Therapist Data Management - Frontend prototype for early testing |
| Weeks 5–7 | **iOS Development & App Store Release** |  |
| Weeks 8–12 | **Model Refinement** | - Add RAG filtering and query context - Implement model memory system |

---

## **4. Development Log**

**Status:** Up to date as of 2025-11-03 — mirror entries with `PROGRESS.md` for granular milestone tracking (latest backend regression run: `pytest`, 92 passed at 07:05 UTC on 2025-11-04).

### **Infrastructure & Platform**

- Terraform baseline revalidated locally on 2025-11-03 with Terraform 1.6.6 (`terraform init -backend=false`, `terraform validate`). Execution of `run_terraform_plan.sh` / `run_terraform_apply.sh` stays blocked pending Azure service principal + AWS role credentials; once supplied, apply outputs (AKS kubeconfig, S3 bucket ARNs, IAM role ARN) will be captured for CI runners.
- 2025-11-04: Added `infra/scripts/check_cloud_prereqs.sh` and the AKS provisioning runbook (`docs/runbooks/aks_provisioning.md`) so platform engineers can perform preflight checks and follow a guided apply/validation sequence when credentials land.

### **Business Logic & Backend**

#### **Account Management**

- Username/password login ✅ *(deprecated before launch)*
- SMS login ✅ *(OTP challenge + verification shipped in `services/backend/app/services/auth.py` with mobile/web flows.)*
- Third-party account integration (Google, etc.) ✅ *(Google OAuth stub client + token exchange live across backend/web/mobile.)*
- Token renewal ✅

#### **Chat System**

- Persistent conversation storage
  - Real-time chat logging ✅ *(message-level S3 persistence via ChatTranscriptStorage)*
  - Daily chat snapshot storage ✅ *(persisted to S3 via ChatTranscriptStorage)*
- Summary generation
  - Daily summaries ✅ *(pipeline implemented via Summary Scheduler Agent)*
  - Weekly summaries ✅ *(weekly aggregation + storage complete)*
- Guided chat templates for common scenes ✅ *(curated dataset `chat_templates.json`, `/api/chat/templates`, and web quick-start chips).*

#### **Model Integration**

- Static model response ✅ *(deprecated before launch)*
- Debug-stage raw model integration ✅ *(Azure-first orchestrator with AWS Bedrock fallback now covered by `tests/test_llm_orchestrator.py`.)*
- Intelligent agent integration ✅ *(Conversation memory, recommendations, and evaluation guardrails wired into chat orchestration.)*

#### **Pilot Feedback**

- Structured intake ✅ *(`PilotFeedback` persistence + `/api/feedback/pilot` endpoints with regression tests `test_feedback_service.py` / `test_feedback_api.py` capture cohort sentiment and blockers.)*
- Feedback aggregation CLI ✅ *(`mindwell-pilot-feedback-report` summarizes sentiment/trust/usability scores and top tags to inform backlog triage.)*
- Feedback summary API ✅ *(`/api/feedback/pilot/summary` unlocks dashboard integrations for backlog prioritization.)*
- UAT session logging ✅ *(New `PilotUATSession` model + `/api/uat/sessions` API and `mindwell-uat-sessions` CLI capture facilitator logs with regression coverage in `services/backend/tests/test_pilot_uat_service.py` and `services/backend/tests/test_pilot_uat_api.py`.)*

#### **Pilot Cohort Recruitment**

- Participant roster management ✅ *(New `PilotCohortParticipant` model, service `/api/pilot-cohort`, and CLI `mindwell-pilot-cohort` track invites/onboarding with regression coverage in `test_pilot_cohort_service.py` / `test_pilot_cohort_api.py`.)*
- Cohort engagement automation ✅ *(`plan_followups` heuristics, `/api/pilot-cohort/participants/followups`, and CLI `mindwell-pilot-followups` surface templated outreach and cadence planning.)*
- Operational runbook ✅ *(`docs/runbooks/pilot_cohort_recruitment.md`) aligns recruitment, facilitation, and backlog triage steps so the remaining UAT milestone can be executed without additional engineering support.*

#### **Therapist Data**

- list/get API ✅
- Script for scraping therapist data and injecting into database ✅ *(Data Sync agent `mindwell-data-sync` publishes normalized profiles to `S3_BUCKET_THERAPISTS`.)*
- Internationalization (i18n) of therapist information ✅

#### **Data Governance & Privacy**

- Retention automation ✅ *(Summary Scheduler + `mindwell-retention-cleanup` enforce S3/database purge windows.)*
- Subject access/export tooling ✅ *(SAR scripts in `services/backend/scripts/` backed by `DataSubjectService` and tests.)*
- PII deletion/redaction flow ✅ *(`delete_user_data.py` scrubs chat content, revokes tokens, and anonymises analytics/summary artefacts.)*

#### **AWS Integration**

- RDS ✅ *(Terraform modules `infra/terraform/aws_network.tf` + `aws_rds.tf` provision an optional PostgreSQL replica with Secrets Manager credentials seeding.)*
- EC2 instances ✅ *(Automation agent host defined in `infra/terraform/aws_ec2_agents.tf` runs Data Sync/Summary Scheduler workloads with controlled SSH ingress.)*

---

## **5. Intelligent Agent Functionality**

### **Core Modules**

- **Daily Conversation Summary**
  - Title
  - Overview
  - “Spotlight”: one-line highlight or distilled insight
- **Weekly Summary**
  - Generate cumulative summaries
- **Full Conversation History**
  - Create global prompt context
  - Extract recurring discussion topics

### **Therapist Recommendation**

- Context injection and prompt standardization
- Prompt evaluation
- Text vectorization and semantic retrieval

---

## **6. Mobile Application**

### **Login & Authentication**

- Account-based login ✅ *(deprecated later)*
- SMS login
- Third-party account integration
- Token renewal

### **Chat Functionality**

- Streamed response integration ✅
- Offline transcript caching ✅ *(AsyncStorage-backed restore in the Expo client.)*
- Push notification scaffolding ✅ *(Expo Notifications registration with device token caching.)*
- **Input Methods:**
  - Text input
  - Voice input via local system model ✅ *(mobile app now uses on-device recognition through `@react-native-voice/voice` with automatic fallback to `/voice/transcribe` when unsupported.)*
  - WeChat-style “hold to speak” voice input ✅
  - Auto language detection ✅ *(LanguageDetector service auto-resolves locale -> shared across web/mobile states.)*
  - Server-side ASR (speech recognition) ✅ *(FastAPI `/api/voice/transcribe` plus shared mobile/web integrations.)*
- **Output (Voice Playback):**
  - RN-TTS integration ✅
  - Sentence-level segmentation ✅
  - Adjustable voice rate and tone
  - Option to disable voice playback in Settings
  - Interrupt voice output upon new input trigger

### **Therapist Interface**

- Therapist overview ✅
- Therapist detail page ✅
- Therapist filtering functionality ✅ *(Web/mobile directories expose specialty, language, price, and recommendation filters.)*

### **Explore Page**

- Explore modules for breathing exercises, psychoeducation resources, and trending themes delivered via feature flags and personalized data pipelines. (✅ prototype shipped)

### **Journey Page**

- **Weekly Reports (Past 10 Weeks)**
- **Daily Reports (Past 10 Days)**
  - Title + Spotlight (clickable to detail page)
  - Detail View:
    - **Tab 1:** Date, Title, Spotlight, Summary
    - **Tab 2:** Chat Records
- ✅ Expo Journey dashboard implements the flows above with locale-aware summaries, transcript toggles, and manual refresh (`JourneyScreen`, `useJourneyReports`, `services/reports`).

### **Localization**

- Chinese interface support (i18n)

### **Platform Adaptation**

- iOS optimization
  - Static checklist captured in `docs/mobile_performance.md` (gesture/safe-area audit). Simulator validation still pending scheduling.
- Android optimization
  - Baseline bundle profile generated on 2025-11-02 via `npm run profile:android` (see `docs/mobile_performance.md` Validation Log).

---

## **7. Deployment & Operations**

**Status:** Release management handbook published (`docs/release_management.md`) with changelog (`docs/changelog.md`) seeded; automation agents documented in `AGENTS.md`.

### **Bug Tracker**

| **Issue** | **Description** | **Status** |
| --- | --- | --- |
| /therapy/chat/stream triggers “access denied” | Does not affect pre-request validation but returns error post-request | Resolved – added `/api/chat/stream` endpoint + legacy `/therapy/chat/stream` alias with SSE error handling |

---

## **8. Additional Notes**

- Integration with Google and WeChat third-party account management platforms available in dev (full production credential exchange still a future milestone).
- Release artefact pipeline `.github/workflows/release.yml` produces backend wheels plus web/mobile bundles for tag builds and manual dispatch.
- Investor/partner summary brief lives in `docs/investor_partner_brief.md` for fundraising and partnership outreach.

---

Would you like me to also convert this into a **formatted technical document template (e.g., Markdown → PDF or DOCX)** with consistent section numbering, table of contents, and company footer branding (e.g., “MindWell Confidential – 2025”)? That would make it suitable for investor decks or engineering sprints.
