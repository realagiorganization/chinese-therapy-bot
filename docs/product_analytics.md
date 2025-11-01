# MindWell Product Analytics Overview

This document outlines the new product analytics instrumentation shipped with the MindWell platform. It covers event taxonomy, data storage, aggregation surfaces, and operational workflows needed by the Growth and Strategy teams.

## 1. Event Taxonomy

Events are normalized into the `analytics_events` table (Postgres) with the following schema:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID (nullable) | User responsible for the interaction |
| `session_id` | UUID (nullable) | Chat session identifier when applicable |
| `event_type` | `varchar(64)` | Canonical identifier (see table below) |
| `funnel_stage` | `varchar(32)` | `engagement`, `consideration`, `conversion`, `retention`, etc. |
| `properties` | JSONB | Flexible payload for experiment metadata |
| `occurred_at` | timestamptz | UTC timestamp supplied by client/server |
| `created_at` | timestamptz | UTC ingestion timestamp |

### Canonical Event Types

| Event | Funnel Stage | Description | Key Properties |
| --- | --- | --- | --- |
| `chat_turn_sent` | Engagement | User submits a chat turn to the assistant | `locale`, `message_length` |
| `therapist_profile_view` | Consideration | Therapist profile/detail screen rendered | `therapist_id`, `locale` |
| `therapist_connect_click` | Conversion | CTA to connect with therapist clicked | `therapist_id`, `locale`, `entry_point` |
| `summary_viewed` | Retention | Daily/weekly summary opened | `summary_type` (`daily`/`weekly`) |
| `journey_report_view` | Retention | Journey conversations feed accessed | `report_kind` |
| `signup_started` | Activation | Account creation flow initiated | - |
| `signup_completed` | Conversion | Account creation completed | - |
| `custom` | varies | Arbitrary events supplied via `/api/analytics/events` | Arbitrary |

> Additional event types can be introduced safely by POSTing to `/api/analytics/events`. They will automatically roll into the aggregation pipeline.

## 2. Data Capture Points

- **ChatService** records a `chat_turn_sent` event for every user utterance along with locale detection metadata.
- **TherapistService** records `therapist_profile_view` events whenever detail pages (including seed fallbacks) are returned.
- **ReportsService** records `summary_viewed` and `journey_report_view` events as users access generated insights.
- **Clients** (web/mobile) can emit supplemental events via the public `/api/analytics/events` endpoint when users trigger UI conversions (e.g., CTA taps).

## 3. Aggregation & Access Surfaces

- **API Summary** – `GET /api/analytics/summary?window_hours=<n>` returns aggregated journey engagement and funnel conversion metrics. Default lookback window is 24 hours and can extend up to 14 days.
- **CLI Agent** – `mindwell-analytics-agent --window-hours 168 --output analytics-summary.json` generates the same summary offline and optionally writes JSON to disk/S3 for downstream analysis.
- **Monitoring Agent** – Consumption (e.g., retention delta) can be added to existing alerts by querying the `analytics_events` table or CLI output.

The summary payload contains:

- `engagement.active_users`: distinct users interacting within the window.
- `engagement.avg_messages_per_session`: chat message density per active session.
- `engagement.therapist_conversion_rate`: ratio of connect clicks to profile views.
- `conversion.signup_completion_rate`: ratio of completed sign-ups to initiated flows.

## 4. Operational Guidance

1. **Schema Management:** Alembic revision `20240704_0002` creates `analytics_events` with stage/type indexes for efficient slicing. Apply migrations before enabling instrumentation.
2. **Data Retention:** Classified as Category C operational metadata (see `docs/data_governance.md`). Retain indefinitely for cohort analysis, but respect deletion requests tied to `user_id`.
3. **Client Integration:** Web/mobile product squads can call `POST /api/analytics/events` with `AnalyticsEventCreate` payloads. Schema validation ensures consistent taxonomy, while allowing experimental properties.
4. **Growth Reporting:** Run `mindwell-analytics-agent` on a cron (e.g., hourly) and push resulting JSON snapshots to the Growth team’s S3 prefix (`growth/analytics/<date>.json`). These snapshots power funnel dashboards and gameplan reviews.

## 5. Next Steps

- Integrate analytics summary output with the Monitoring Agent to alert on sharp dips in therapist conversion rate or engagement.
- Extend event taxonomy with experiment identifiers (A/B buckets) once feature flag targeting is wired in.
- Surface summary highlights inside the operator console to inform therapist staffing decisions.
