---
title: Pilot Cohort Recruitment & UAT Runbook
---

# Pilot Cohort Recruitment & UAT Execution Runbook

This runbook operationalizes the remaining Phase 6 Quality Assurance milestone: **recruit pilot users, gather structured feedback, and feed the iteration backlog**. It stitches together existing backend tooling so operations, research, and engineering stay in sync.

---

## 1. Stakeholders & Prerequisites

- **Stakeholders:** Growth (recruitment), Research (facilitation), Product/Engineering (triage).
- **Systems touched:** Postgres (pilot tables), S3 feedback artifacts, Slack/Teams alert channels, dashboards.
- **Prerequisites:**
  - Backend deployed (local tunnel or staging environment).
  - Access to the database (for migrations) and API keys/credentials (see `ENVS.md`).
  - CLI access to the repository virtual environment (`pip install -e .[dev]`).
  - `docs/uat_plan.md` reviewed for success metrics and consent requirements.

Activate the backend virtual environment before running any CLI examples:

```bash
cd services/backend
poetry shell  # or source .venv/bin/activate, depending on your setup
```

---

## 1b. Dry-Run the Pilot Workflow (Optional but Recommended)

Before inviting real participants, rehearse the full data flow with synthetic data:

1. Ensure you have a local database ready and access to the Alembic migrations (`DATABASE_URL` must point to a writable instance).
2. Run the dry-run helper to generate sample participants, feedback, and UAT sessions, then materialize a Markdown summary:

   ```bash
   python services/backend/scripts/uat_dry_run.py \
     --database-url sqlite+aiosqlite:///./uat_dry_run.db \
     --init-db \
     --generate-samples \
     --overwrite-samples \
     --purge-existing \
     --cohort pilot-demo \
     --seed 42 \
     --report-path docs/uat_dry_run_report.md
   ```

   - Add `--participants`, `--feedback`, or `--uat-sessions` to enlarge the sample.
   - Omit `--init-db` if your schema is already migrated; leaving it on helps first-time rehearsals.
3. Review `docs/uat_dry_run_report.md` to confirm the backlog, sentiment, and cohort metrics look sensible before onboarding live testers.

> ⚠️ If migrations are missing in your checkout, the `--init-db` step will fail; run against an environment that already has the pilot tables or apply the outstanding revisions manually.

---

## 2. Seed the Pilot Cohort Roster

1. Prepare a CSV with the headers documented in `services/backend/scripts/manage_pilot_cohort.py` (minimum recommended columns: `alias,email,phone,locale,status,source,tags,consent`).
2. Import the CSV into the database:

   ```bash
   mindwell-pilot-cohort import ./pilot_cohort_seed.csv \
     --cohort fall-2025 \
     --channel wechat \
     --locale zh-CN
   ```

   - Add `--dry-run` during rehearsals.
   - Each row defaults to the CLI flags when the CSV omits a value.
3. Verify the roster:

   ```bash
   mindwell-pilot-cohort list --cohort fall-2025 --status invited --limit 20
   ```

4. Share the roster export with the Growth team if they use an external CRM (CSV export lives in the command output).

---

## 3. Drive Recruitment & Onboarding

1. Engineers/Growth update participant records as responses arrive:

   ```bash
   mindwell-pilot-cohort update <participant-uuid> \
     --status scheduled \
     --consent true \
     --tags "wechat|vip"
   ```

2. Schedule follow-ups for participants who have not replied:

   ```bash
   mindwell-pilot-followups --cohort fall-2025 --status invited --format table
   ```

   The CLI prints priority, recommended cadence, and template copy. Push actionable tasks to the Support/Success channel.
3. Log manual outreach in the `notes` field so the automation agent can avoid duplicate nudges.

---

## 4. Run UAT Sessions

1. Facilitators record each session via the UAT CLI or API:

   ```bash
   mindwell-uat-sessions create \
     --participant <participant-uuid> \
     --session-date 2025-11-10T13:00:00+08:00 \
     --satisfaction 4 \
     --trust 3 \
     --summary "Focused on managing exam stress; flagged translation rough edges." \
     --follow-up "Send mindfulness resources; schedule therapist intro"
   ```

2. Attach transcripts or screen recordings to the shared storage bucket (`mindwell-dev-summaries`) using the participant UUID as the key prefix.
3. Any critical issues discovered during sessions should trigger incident response via `docs/operations/incident_response.md`.

---

## 5. Capture Pilot Feedback

1. Encourage participants to submit feedback through the product UI or via facilitators using the Feedback API:

   ```bash
   http POST https://<backend>/api/feedback/pilot \
     participant_id=<uuid> \
     rating=5 \
     sentiment="positive" \
     highlights:='["Loved tone", "Wants more breathing exercises"]' \
     blockers:='["Voice playback paused unexpectedly"]'
   ```

   (Use authenticated requests; see `README.md` for token retrieval.)
2. Run the summary CLI daily:

   ```bash
   mindwell-pilot-feedback-report --cohort fall-2025 --format markdown > pilot-feedback.md
   ```

   Share the report in the #pilot-feedback channel and attach to the product triage document.

---

## 6. Generate UAT & Feedback Dashboards

- **Aggregated API:** `/api/feedback/pilot/summary` returns sentiment trends and blocker counts.
- **Quick analytics export:**

  ```bash
  http GET https://<backend>/api/feedback/pilot/summary?cohort=fall-2025 \
    "Authorization: Bearer <token>" \
    > feedback-summary.json
  ```

- Feed the JSON output into the Looker/Power BI dashboard pipeline. The Monitoring Agent can push alerts if negative sentiment crosses thresholds.

---

## 7. Prioritize the Iteration Backlog

1. Combine `pilot-feedback.md`, `feedback-summary.json`, and `mindwell-pilot-followups` output.
2. During the weekly triage meeting:
   - Review top blockers and merge duplicates.
   - Assign each blocker to an engineering owner with a target release (Week N+1 for critical issues).
   - Update `docs/changelog.md` with committed fixes tied to participant IDs.
3. Close the loop with participants via `mindwell-pilot-followups --notify` (or manual messaging) once fixes ship.

---

## 8. Archival & Compliance

- Keep raw feedback and session logs under the retention policies defined in `docs/data_governance.md`.
- Use `mindwell-data-sync` and `mindwell-retention-cleanup` agents to enforce S3/database retention windows.
- For subject access requests, run `mindwell-data-subject-export --participant <uuid>` and share the zipped archive with Legal/Privacy.

---

## 9. Checklist Summary

| Step | Owner | Tooling |
| --- | --- | --- |
| Seed roster | Growth / Eng | `mindwell-pilot-cohort import` |
| Follow-up cadences | Growth | `mindwell-pilot-followups` |
| Run sessions | Research | `mindwell-uat-sessions` |
| Collect feedback | Research / Product | Feedback API & `mindwell-pilot-feedback-report` |
| Prioritize backlog | Product / Eng | Reports + triage meeting |

Track completion status in `PROGRESS.md` under Phase 6 once participants are onboarded and feedback loops have produced backlog updates.
