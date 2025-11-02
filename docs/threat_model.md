# MindWell Threat Modeling Snapshot

This document captures the initial threat modeling exercise requested in `DEV_PLAN.md` Phase 6 and aligns with the Automation Agents in `AGENTS.md`. It will be refined as infrastructure is provisioned and new services ship.

## 1. Scope & Critical Assets
- **User PII & Conversational Data:** Stored in Azure PostgreSQL (`users`, `chat_sessions`, `chat_messages`) and summarized artifacts in AWS S3 (`S3_CONVERSATION_LOGS_BUCKET`, `S3_BUCKET_SUMMARIES`).
- **Therapist Directory:** Canonical JSON written by the Data Sync Agent to `S3_BUCKET_THERAPISTS` and hydrated into Postgres.
- **Credential Stores:** Azure Key Vault, AWS Secrets Manager, GitHub OIDC federation secrets.
- **Model Integrations:** Azure OpenAI / Bedrock API keys, prompt templates, evaluation pipelines.
- **CI Runner Outputs:** Container images, Terraform plans, build logs executed on self-hosted EC2 runners.

## 2. Actors & Entry Points
- **External Users:** Web/mobile clients invoking FastAPI routes (`/chat`, `/auth`, `/reports`).
- **Therapists/Admins:** Access management tools, import pipelines, reporting surfaces.
- **Automation Agents:** CI Runner, Data Sync, Summary Scheduler, Monitoring (per `AGENTS.md`).
- **Third Parties:** SMS provider, OAuth (Google), AI platforms, Terraform providers.
- **Infrastructure Admins:** Azure/AWS subscription administrators with direct console or CLI access.

Attack surfaces include public APIs (FastAPI, SSE streaming), webhook/event consumers, IaC execution (Terraform, GitHub Actions), agent cron jobs, and storage buckets exposed via misconfiguration.

## 3. Data Flow Overview
1. Clients authenticate (SMS OTP or Google OAuth) through `AuthService` and receive JWT tokens (`services/backend/app/services/auth.py`).
2. Chat messages stream to FastAPI (`/api/chat/stream`, legacy alias `/therapy/chat/stream`), orchestrated by `ChatService` (`services/backend/app/services/chat.py`) which persists transcripts to Postgres and S3.
3. Summary Scheduler Agent (`services/backend/app/agents/summary_scheduler.py`) reads chat history, generates summaries via LLM orchestrator, and stores results in S3 through `SummaryStorage`.
4. Data Sync Agent ingests therapist data into S3, then ETLs into Postgres.
5. CI Runner applies Terraform (`infra/terraform/*.tf`) and deploys containers; outputs handled by GitHub Actions workflow `ci.yml`.

## 4. Threat Scenarios & Mitigations

| Scenario | Impact | Current Mitigations | Follow-ups |
| --- | --- | --- | --- |
| **Compromised JWT/Refresh Tokens** via theft or replay | Account hijack, data exposure | Refresh tokens hashed (`AuthService._hash_secret`), TTL constrained, `RefreshToken` table tracks issued tokens | Add device binding & anomaly detection; enforce token revocation on logout |
| **Weak OTP Generation** exploited by brute force | Unauthorized login | OTPs now use `secrets.choice` and normalized phone numbers (`services/backend/app/services/auth.py:200-265`) | Rate-limit OTP verification per IP/device; add SMS provider audit logs |
| **S3 Bucket Misconfiguration** leaking transcripts | Privacy breach | Buckets defined private in Terraform (`infra/terraform/aws_storage.tf`), uploads use IAM roles, transcripts pseudonymized | Enable S3 bucket policies enforcing TLS, add Macie scans, periodic access review |
| **LLM Prompt Injection / Jailbreak** | Malicious responses, data leak | Prompt templating centralised (`app/integrations/llm.py`), evaluation service monitors outputs, guardrail heuristics exist (`services/backend/app/services/evaluation.py`) | Integrate automated red teaming, add content filtering before reply streaming |
| **CI Secrets Exposure** on self-hosted runners | Broad infra compromise | GitHub Actions now runs `pip-audit`, `bandit`, and `gitleaks` (`.github/workflows/ci.yml`) with `.gitleaks.toml` allowlist | Lock down runner IAM roles, enable GitHub OIDC fine-grained permissions, add dependency review gate |
| **Terraform Drift / Credential Reuse** | Untracked infra changes | Remote state configured (`infra/terraform/backend.hcl.example`), state locking, Key Vault secret rotation runbooks | Automate `terraform plan` in CI with manual approvals, integrate drift detection (Azure Policy, AWS Config) |
| **Agent Credential Abuse** | Unauthorized data mutation | Agents use scoped IAM identities, Summary Scheduler pulls settings via `get_settings()` without hardcoded secrets | Add per-agent service principals with least privilege, monitor scheduler outputs for anomalies |
| **LLM API Key Leakage** in logs or code | Loss of AI access, billing impact | Secrets sourced from Key Vault / Secrets Manager, `.gitleaks.toml` blocks sample docs only | Extend secret scanning pre-commit, mask sensitive env vars in logging configuration |

## 5. Security Controls Roadmap
1. **Automated Scanning:** Dependency (`pip-audit --skip-editable`), static (`bandit`), and secret scanning (`gitleaks`) run in CI; failures block merges.
2. **Threat Detection:** Expand Monitoring Agent alerts to include abnormal API usage, high error rates, or unexpected cost spikes.
3. **Governance:** Document data retention and anonymization workflows (pending Phase 6 tasks in `PROGRESS.md`), and map regulatory obligations (PIPL, GDPR).
4. **Incident Response:** Draft incident response playbooks covering data breach, AI misuse, and infrastructure compromise scenarios.

## 6. Assumptions & Open Risks
- Terraform has not yet been applied; cloud controls exist as code but require enforcement post-deployment.
- Self-hosted CI runners assume hardened AMIs; additional hardening (patch cadence, access logging) required.
- Mobile clients share backend auth flows; mobile-specific threats (reverse engineering, certificate pinning) slated for Phase 7.
- Data Sync Agent relies on upstream therapist sources providing sanitized data; need validation pipeline for PII correctness.

> This threat model is a living document. Review after each major release or architectural change, and during regular security review cycles.
