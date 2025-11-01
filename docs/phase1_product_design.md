# Phase 1 – Core Product Design

This document fulfills the Phase 1 deliverables defined in `PROGRESS.md` and `DEV_PLAN.md`. It outlines user journeys, chatbot–therapist integration logic, the conversation history schema with retention policy, and UX wireframe specifications for the core MindWell surfaces.

## 1. User Journeys

### 1.1 Chatbot Therapy Session (Primary Flow)
- **Actors:** End user, Chatbot (LLM), Monitoring Agent.
- **Trigger:** User opens app/web client and selects "Start Session".
- **Steps:**
  1. Chat UI loads the most recent conversation context (last 20 exchanges) via `/sessions/{id}/context`.
  2. User submits text, voice, or mixed input; voice input uses on-device ASR fallback with optional server transcription.
  3. Chat service calls AI orchestrator (Azure OpenAI primary, AWS Bedrock fallback) with memory slice + therapist hints.
  4. Streaming response surfaces token-by-token; TTS playback optional.
  5. Message, model metadata, and sentiment scores persist to Postgres + streaming log topic.
  6. Summary Scheduler Agent tags the session for inclusion in daily/weekly jobs.
- **Outcomes:** Updated conversation thread, optional therapist recommendations, telemetry emitted for monitoring.

### 1.2 Therapist Browsing & Matching
- **Actors:** End user, Data Sync Agent, Therapist API.
- **Trigger:** User navigates to Therapist Explore page or receives in-session recommendation.
- **Steps:**
  1. Therapist list API returns segmented results (by specialty, language, availability).
  2. User filters by modality, region, price range; Data Sync Agent maintains source-of-truth directory in `S3_BUCKET_THERAPISTS`.
  3. Selecting a therapist opens detail profile with bio, credentials, availability, and sample audio/video highlights.
  4. User can bookmark, request intro, or add to active therapist rotation (max 3 simultaneously).
  5. If user connects, chat session metadata associates therapist ID for follow-up.
- **Outcomes:** Potential match recorded, feedback loop informs recommendation engine.

### 1.3 Progress Tracking & Journey Reports
- **Actors:** End user, Summary Scheduler Agent, Backend Reports API.
- **Trigger:** User opens Journey page or receives notification of new summary.
- **Steps:**
  1. Journey page fetches latest daily (10) and weekly (10) summaries from `/reports/{userId}`.
  2. Daily report card shows title, spotlight insight, mood trend chip; tapping opens detail tabs (Summary vs. Chat Log).
  3. Weekly report aggregates highlights, top themes, therapist touchpoints, and action items.
  4. User can share reports securely with therapist (expiring link) or export PDF for personal records.
  5. Historical metrics (mood scores, interaction cadence) overlay charts for trends.
- **Outcomes:** Reinforced engagement, data persistence for longitudinal analysis.

## 2. Chatbot–Therapist Integration Logic

### 2.1 Recommendation Triggers
- **Proactive:** After sentiment dip >2 points over three sessions, or when user expresses need for human support.
- **Reactive:** User asks explicitly for therapist or accepts in-chat prompt like “Would you like to speak with a professional?”
- **Scheduled:** Weekly summary pipeline identifies therapy-ready cues (e.g., recurring themes, risk keywords).

### 2.2 Data Flow
1. Chat Orchestrator emits `session_events` Kafka topic entry with sentiment, topics, and risk flags.
2. Therapist Recommendation Engine consumes topic, calculates top matches using embeddings + rules.
3. Recommendation stored in `session_recommendations` table and cached for low-latency retrieval.
4. Chat UI fetches recommendation bundle when trigger conditions met; displays inline card with CTA.
5. User actions (dismiss, save, connect) log back to engine for reinforcement and monitoring.

### 2.3 Therapist Availability Sync
- Data Sync Agent normalizes therapist roster from partner sources, writing canonical JSON to S3.
- Admin import job hydrates Postgres tables via ETL, mapping availability blocks and localization assets.
- Conflicts resolved using “most recent update wins” with audit logs stored for compliance.

### 2.4 Handoff Protocol
- When user schedules a session, chatbot stores therapist assignment and passes last summaries via secure API.
- During therapist-led session, chatbot enters assist mode (suggested prompts, note-taking) with read-only view.
- Post-session, therapist can append manual notes; Summary Scheduler Agent merges with automated insights.

## 3. Conversation History Schema & Retention

### 3.1 Core Tables (Azure PostgreSQL)
| Table | Purpose | Key Columns |
| --- | --- | --- |
| `users` | Profile + settings | `id`, `phone`, `locale`, `risk_opt_in`, `created_at` |
| `sessions` | Conversation container | `id`, `user_id`, `therapist_id`, `status`, `started_at`, `ended_at` |
| `messages` | Streaming chat logs | `id`, `session_id`, `role`, `content`, `tokens_in`, `tokens_out`, `sentiment_score`, `created_at` |
| `session_recommendations` | Therapist suggestions | `id`, `session_id`, `therapist_ids`, `trigger_reason`, `confidence`, `created_at` |
| `daily_summaries` | 24h digest | `id`, `user_id`, `summary_date`, `title`, `spotlight`, `insights`, `mood_delta`, `source_pointer` |
| `weekly_summaries` | 7-day rollup | `id`, `user_id`, `week_start`, `themes`, `actions`, `risk_level`, `source_pointer` |
| `journey_metrics` | Derived analytics | `id`, `user_id`, `metric_type`, `metric_value`, `captured_at` |

### 3.2 Object Storage Layout (Azure Blob + AWS S3 Mirror)
- `logs/{userId}/{sessionId}/message_{ts}.jsonl` – immutable message stream with trace metadata.
- `summaries/daily/{userId}/{date}.json` – structured daily summaries with embedding vectors for search.
- `summaries/weekly/{userId}/{weekStart}.json`
- `therapists/{therapistId}/profile_{locale}.json` – Data Sync Agent output.

### 3.3 Retention Policy
- **Real-time Logs:** Retained 18 months online; archived to Glacier Deep Archive thereafter with delete eligibility after 24 months unless legal hold.
- **Daily Summaries:** 24-month retention; user can request purge (GDPR compliant). Backups encrypted with CMK.
- **Weekly Summaries & Metrics:** Kept indefinitely for longitudinal tracking unless user opts out.
- **PII Handling:** Phone numbers stored encrypted at rest; access via service principals with least privilege.

### 3.4 Access Controls
- Backend services authenticate via Azure Managed Identity.
- Therapists receive scoped tokens limiting access to assigned users and summary snapshots.
- Monitoring Agent holds read-only metrics role; no direct PII access.

## 4. UX Wireframe Specifications (Textual)

### 4.1 Chatbot Screen
- **Layout:** Sticky header with session title + therapist avatar (if assigned); center pane for message stack with alternating bubbles and timestamp chips.
- **Input Row:** Text box, mic button (press-to-speak), attachment icon (future use), send button that doubles as stop streaming.
- **Assist Panel:** Collapsible right rail on tablet/desktop showing suggested prompts, recent emotion trend.
- **States:** Default, streaming (shows typing indicator + wave animation), escalation (therapist recommendation card), offline (retry banner).

### 4.2 Therapist Showcase
- **Grid/List Toggle:** Cards show name, tagline, price, response time badge.
- **Filters Drawer:** Specialty (multi-select), modality, language, availability, insurance.
- **Detail View:** Hero image/video, credentials (tag chips), biography, expertise tags, booking CTA, testimonial carousel, schedule widget with timezone awareness.
- **Recommendation Badge:** Displays “Recommended for you” with reason snippet (e.g., “CBT focus, Mandarin-speaking”).

### 4.3 Journey Reports
- **Dashboard Header:** Mood trend chart, weekly engagement streak, shortcut to export PDF.
- **Daily Report Cards:** Carousel of cards with title, spotlight, colored mood chip; selecting opens modal with tabbed content (Summary / Chat Log / Action Items).
- **Weekly Report View:** Timeline view with stacked segments (Highlights, Themes, Therapist Interactions, Suggested Exercises).
- **Notifications:** Badge counts indicate unread reports; tapping clears after viewing.

### 4.4 Explore Page Prototype
- **Hero Section:** Rotating educational modules (video/text) sourced from curated therapist content.
- **Sections:** “Mindfulness Tools,” “Community Stories,” “Upcoming Events,” each module card deep-links to detailed content or external webinars.
- **Personalization Hooks:** Uses recent topics and mood trends to rank modules; includes opt-out toggle for personalization.
- **Cross-platform Considerations:** On mobile, vertical scroll with sticky quick filters; web uses 2-column layout with featured content and resource sidebar.

## 5. Assumptions & Dependencies
- Azure AKS remains primary deployment; AWS resources used for redundancy and Bedrock access.
- Localization prioritizes Simplified Chinese with English fallback; i18n files stored alongside UI components.
- Voice features depend on existing RN-TTS integration and planned server-side ASR pipeline.
- Compliance reviews (HIPAA-equivalent) scheduled in Phase 6; current design anticipates required audit logs.

## 6. Open Questions
- Define SLA for therapist response time once a recommendation is accepted.
- Clarify legal requirements for storing therapist notes alongside automated summaries in target markets.
- Determine whether Explore page includes community interaction (comments) or remains content-only in MVP.

