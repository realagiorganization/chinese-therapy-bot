# Runbook – Therapist Data Sync Agent

## Scope
The Data Sync agent (`services/backend/app/agents/data_sync.py`) ingests therapist rosters from configured sources and publishes normalized payloads to `S3_BUCKET_THERAPISTS`. This runbook resolves ingestion failures or data quality regressions.

## 1. Signals & Detection
- Monitoring Agent alert (`TherapistRosterFreshness`) exceeds threshold (default >6 h without update).
- Support ticket indicating missing therapists or stale metadata.
- Data Sync workflow failure notification from CI Runner agent.

## 2. Immediate Checks
1. Inspect latest run logs (`logs/agents/data-sync/<date>.log` or GitHub Actions run output).
2. Verify S3 bucket objects `therapists/<locale>/profile_*.json` updated within SLA.
3. Confirm upstream sources reachable (HTTP 200) using `scripts/agents/fetch_therapists.py --source <id>`.

## 3. Common Recovery Actions
- **Transient HTTP failures:** Rerun agent with exponential backoff `poetry run mindwell-data-sync --retry`.
- **Schema changes:** Update normalizer in `DataSyncAgent._normalize_record`, add new fields to `TherapistProfileSchema`.
- **Credential issues:** Rotate AWS credentials via Terraform outputs; ensure CI Runner role still assumes `S3TherapistWriter`.

## 4. Validation
1. Run unit tests `pytest services/backend/tests/test_data_sync_agent.py -q`.
2. Execute dry-run `mindwell-data-sync --dry-run --source http-json --locale zh-CN` to review normalized payload.
3. Confirm downstream APIs (`/api/therapists?locale=zh-CN`) reflect refreshed data.

## 5. Post-Recovery
- Document fix in incident timeline and update retention clean-up schedules if dataset size changed.
- Notify Summary Scheduler agent owner if therapist recommendations rely on refreshed embeddings.
