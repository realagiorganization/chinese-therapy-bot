# Data Governance & Retention Plan

This document captures the policies and technical controls that govern personal data handled by MindWell. It complements the infrastructure and security artefacts referenced in DEV_PLAN Phase 6.

## 1. Data Classification
- **Category A – Critical PII:** Full name, phone number, email address, government ID (if ever collected). Stored in Postgres within encrypted columns; access restricted to Auth and Therapist admin services.
- **Category B – Sensitive Therapy Data:** Chat transcripts, summaries, therapist recommendations. Stored in Postgres and S3 with server-side encryption (SSE-S3). Access limited to backend services via IAM roles.
- **Category C – Operational Metadata:** Feature flag states, analytics events, system logs. Retained for troubleshooting with lower privacy risk.

## 2. Retention Schedule
| Dataset | Storage | Retention | Disposal Mechanism | Owner |
| --- | --- | --- | --- | --- |
| Chat transcripts (Category B) | Postgres + S3 `conversation` prefix | 24 months | Scheduled purge job `mindwell-retention-cleanup --include conversations` removes aged S3 objects; database cleanup follows SAR workflow | Platform Engineering |
| Daily summaries | Postgres + S3 `summaries/daily` | 24 months | `mindwell-retention-cleanup --include summaries` deletes objects past retention; Glacier transition optional via lifecycle rules | Summary Scheduler Agent |
| Weekly summaries | Postgres + S3 `summaries/weekly` | Indefinite | Retained for longitudinal analytics unless user requests deletion | Summary Scheduler Agent |
| Product analytics events | Postgres `analytics_events` | Indefinite (review quarterly) | Anonymised when processing deletion requests; growth snapshots pruned via automated job | Growth Analytics |
| Therapist profiles | Postgres + S3 `therapists/` | Until superseded | Data Sync Agent overwrites locale-specific objects and archives previous snapshot for 90 days | Data Ops |
| Authentication logs | Postgres `auth_audit` | 18 months | Database job truncates partitions older than 18 months | Platform Engineering |
| Monitoring telemetry | Azure Application Insights | 30 days | Daily purge using `az monitor app-insights component purge` | SRE |

## 3. Data Subject Requests (SAR/Deletion)
1. Requests land in Zendesk under the *Privacy* queue.
2. Support escalates to Privacy lead within 1 business day.
3. Privacy lead triggers automated workflow using the SAR CLI utilities in `services/backend/scripts/`:
   - Identify the correct account with `python services/backend/scripts/find_user.py --email user@example.com`.
   - Generate the evidence bundle `python services/backend/scripts/export_user_data.py <user-id> --output exports/<user-id>.json`.
   - Execute deletion/redaction via `python services/backend/scripts/delete_user_data.py <user-id>`, optionally dry-running with `--dry-run`.
     - Chat transcripts are scrubbed to `[redacted]`.
     - Daily/weekly summaries are deleted from Postgres and S3.
     - Refresh tokens are revoked and analytics events anonymised with timestamps.
4. Capture the report output and upload to the Privacy register alongside Zendesk ticket metadata.

## 4. Encryption Controls
- **In transit:** All public endpoints served via HTTPS with TLS 1.2+. Internal service-to-service communication within AKS uses mTLS (Istio mesh rollout in progress).
- **At rest:** Terraform enforces `server_side_encryption_configuration` for all S3 buckets and `pg_encryption_enabled = true` for Azure Postgres Flexible Server.
- **Key management:** Azure Key Vault serves application secrets; AWS KMS default keys back S3 objects. Keys rotate automatically every 365 days with audit alerts handled by Monitoring Agent.

## 5. Audit & Monitoring
- CloudTrail logs stored in a dedicated, immutable S3 bucket.
- Gitleaks and dependency scanners run on every CI build.
- Quarterly privacy audit checks:
  - SAR resolutions completed within 30 days.
  - Retention jobs executed successfully (validated via Monitoring Agent alerts).
  - Access reviews for Key Vault/Secrets Manager principals.

## 6. Outstanding Work
- Extend CI to run redaction end-to-end tests.
- Coordinate with Legal to publish user-facing privacy notice revisions.
