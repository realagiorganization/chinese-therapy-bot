# Pilot UAT Execution Runbook

This runbook describes how to execute a dry run or live pilot user acceptance testing cycle using the MindWell toolchain. It complements `docs/runbooks/pilot_cohort_recruitment.md` by focusing on session orchestration, data capture, and reporting.

## 1. Pre-flight Checklist
- Backend API reachable from facilitator workstation (`mindwell-api` running locally or via staging).
- Database migrations applied and connection credentials configured.
- Facilitators have CLI access (`poetry run` or `pip install -e .[dev]`) with environment variables set for:
  - `DATABASE_URL`
  - Optional: `APP_ENV`, `S3_BUCKET_THERAPISTS`, alerting webhooks.
- Slack/Teams webhook configured when running the monitoring agent.
- Decide whether the cycle uses synthetic data first (recommended) or starts with live participants.

## 2. Generate Synthetic Cohort Data (Optional Dry Run)
Use the auto-generated sample data to validate processes end-to-end before inviting real participants.

```bash
cd services/backend
poetry run mindwell-pilot-samples \
  --cohort pilot-dryrun \
  --participants 8 \
  --feedback 12 \
  --uat-sessions 6 \
  --output-dir ./tmp/pilot-dryrun
```

Outputs:
- `participants.csv`: compatible with `mindwell-pilot-cohort import`.
- `feedback.jsonl`: payloads accepted by `/api/feedback/pilot`.
- `uat_sessions.jsonl`: payloads accepted by `/api/uat/sessions`.

## 3. Load Participant Roster
Import the generated roster (or real CSV) into the pilot cohort service:

```bash
poetry run mindwell-pilot-cohort import \
  ./tmp/pilot-dryrun/participants.csv \
  --cohort pilot-dryrun
```

Verify roster:

```bash
poetry run mindwell-pilot-cohort list --cohort pilot-dryrun
```

## 4. Capture Feedback and UAT Sessions
### Batch import (synthetic):

```bash
poetry run python -m scripts.summarize_pilot_feedback --cohort pilot-dryrun --format human
```

To simulate live submissions:

```bash
poetry run mindwell-uat-sessions log \
  --cohort pilot-live \
  --participant-alias pilot-live-001 \
  --scenario guided-chat \
  --environment staging \
  --platform ios \
  --satisfaction-score 4 \
  --trust-score 4 \
  --issue "Summary spotlight missing key insight:medium"
```

The CLI prompts for highlights, blockers, and action items when not provided via flags.

## 5. Follow-up Automation
- Send templated check-ins with:

```bash
poetry run mindwell-pilot-followups \
  --cohort pilot-live \
  --dry-run
```

- Review recommended outreach in the generated Markdown file (`.mindwell/pilot_followups/*.md`).

## 6. Prioritize Backlog and Summaries
- Backlog aggregation:

```bash
poetry run mindwell-uat-sessions backlog --cohort pilot-live --limit 15
```

- Feedback summary (JSON for dashboards):

```bash
poetry run mindwell-pilot-feedback-report --cohort pilot-live --format json
```

## 7. Monitoring and Alerting
- Run the monitoring agent in dry-run mode during UAT windows to validate App Insights and Cost Explorer integration without dispatching alerts:

```bash
poetry run mindwell-monitoring-agent --dry-run
```

## 8. Post-UAT Checklist
- Export session data for archival/regulatory review:

```bash
poetry run mindwell-uat-sessions export --cohort pilot-live --output pilot-live-uat.json
```

- Export participant data when a pilot member exercises a SAR:

```bash
poetry run python -m scripts.export_user_data --user-id <uuid>
```

- Update `PROGRESS.md` with key findings, and log backlog items via `/api/uat/sessions/backlog`.
- Archive synthetic data by deleting seeded rows or resetting the database before live testing.
