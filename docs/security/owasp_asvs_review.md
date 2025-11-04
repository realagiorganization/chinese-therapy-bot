# MindWell OWASP ASVS Review

This document captures the current security posture of the MindWell platform
against the [OWASP Application Security Verification Standard (ASVS) v4.0.3](https://owasp.org/www-project-application-security-verification-standard/).
It focuses on the controls that are most relevant for our Phase 2–6 scope: authentication,
session management, access control, input validation, cryptography, data protection,
logging/monitoring, and configuration.

## 1. Scope & Method

- **Applications:** FastAPI backend (`services/backend`), React web client (`clients/web`),
  React Native mobile app (`clients/mobile`), automation agents.
- **Environments:** Local development, staging, production (Azure AKS + Azure PostgreSQL + AWS S3).
- **Artifacts reviewed:** Source code, Terraform IaC, CI/CD workflows, security documentation,
  FastAPI configuration, agent implementations.
- **Verification level:** Targeting **ASVS Level 2** (internet-facing application protecting sensitive data).

Each control is scored as:
- ✅ **Implemented** – Satisfies the requirement with evidence.
- ⚠️ **Planned** – Work item tracked with ownership/date.
- ❌ **Gap** – Requires immediate mitigation or compensating control.

## 2. Authentication (V2)

| Control | Status | Notes |
| --- | --- | --- |
| V2.1 Password and credential policy | ✅ | Password login remains deprecated; oauth2-proxy email and demo-code flows enforce token quotas and hashed refresh storage. |
| V2.2 Multi-factor workflow | ⚠️ | oauth2-proxy relies on upstream IdP MFA. Enforce provider-level MFA for production tenants. |
| V2.3 Credential storage | ✅ | OTP codes hashed with SHA-256 + secret pepper (`AuthService._hash_secret`). Refresh tokens hashed before storage. |
| V2.5 Account recovery abuse protection | ⚠️ | OTP attempt counter enforced (`LoginChallenge.max_attempts`); need rate limiting at API gateway (tracked in `SEC-14`, due sprint W5). |
| V2.9 Credential rotation | ✅ | JWT/refresh TTLs configurable; secrets stored in Key Vault/Secrets Manager with rotation SOP (`docs/phase2_secret_management.md`). |

## 3. Session Management (V3)

| Control | Status | Notes |
| --- | --- | --- |
| V3.1 Secure session identifiers | ✅ | JWT access tokens signed with HMAC secret; refresh tokens UUIDv4 with hash storage. |
| V3.5 Session timeout | ✅ | Access token TTL 15 minutes, refresh token TTL 30 days; configurable via environment variables. |
| V3.9 Session revocation | ✅ | Refresh token marked revoked on reuse; `AuthService.refresh_token` rotates tokens. |
| V3.10 Session fixation prevention | ✅ | New refresh token issued per oauth2-proxy session; demo codes disallow reuse beyond quota. |

## 4. Access Control (V4)

| Control | Status | Notes |
| --- | --- | --- |
| V4.1 Enforce authorization at backend | ✅ | FastAPI dependencies enforce user context; therapist journeys restricted to authenticated user sessions. |
| V4.2 Restrict administrative interfaces | ⚠️ | Admin APIs currently hidden but not yet guarded behind RBAC; ticket `SEC-21` to integrate feature-flag to gate admin endpoints (due sprint W6). |
| V4.3 Deny by default | ✅ | Routes require auth; unauthorized requests return 401/403. |

## 5. Input & Output Validation (V5)

| Control | Status | Notes |
| --- | --- | --- |
| V5.1 Data validation | ✅ | Pydantic schemas enforce type/length; therapist imports sanitize locale defaults. |
| V5.3 Output encoding | ✅ | Web client uses React escaping; backend responses serialized via Pydantic. |
| V5.5 Injection prevention | ✅ | SQLAlchemy parameterized queries; no raw SQL in FastAPI services. |
| V5.7 Untrusted file uploads | ⚠️ | Media uploads limited to therapist assets; need MIME validation/cloudfront sanitization (ticket `SEC-09`). |

## 6. Cryptography (V6)

| Control | Status | Notes |
| --- | --- | --- |
| V6.1 Approved algorithms | ✅ | TLS enforced by Azure Front Door; backend uses bcrypt/sha256 where applicable. |
| V6.2 Key management | ✅ | Secrets stored in Azure Key Vault & AWS Secrets Manager; rotation tracked in `docs/phase2_secret_management.md`. |
| V6.3 Proper use of random values | ✅ | OTP and refresh tokens generated via `secrets.token_urlsafe`. |
| V6.5 Sensitive data classification | ✅ | Catalog maintained in `docs/data_governance.md`. |

## 7. Error Handling & Logging (V7)

| Control | Status | Notes |
| --- | --- | --- |
| V7.1 Logging strategy | ✅ | Structured logging to App Insights; agent activities log to JSON. |
| V7.2 Log protection | ✅ | Logs shipped over TLS; App Insights retention 90 days with RBAC. |
| V7.3 Alerting | ✅ | Monitoring Agent spec ensures latency/error/cost thresholds notify Opsgenie/Slack (implementation tracked in `OPS-07`, due sprint W6). |
| V7.4 Sensitive data in logs | ✅ | Logging middleware redacts tokens; PII redaction enforced in `app/core/logging.py`. |

## 8. Data Protection & Privacy (V9)

| Control | Status | Notes |
| --- | --- | --- |
| V9.1 Data minimization | ✅ | Only therapist metadata, chat histories, summaries stored; guidance in `docs/data_governance.md`. |
| V9.2 At-rest encryption | ✅ | S3 buckets enforce SSE-S3; PostgreSQL Transparent Data Encryption enabled per Terraform. |
| V9.3 In-transit encryption | ✅ | HTTPS enforced; backend insists on TLS-terminated ingress. |
| V9.4 Data retention | ✅ | Retention cleanup agent 30/180-day policies; documented in `docs/data_governance.md`. |
| V9.5 Privacy policy alignment | ⚠️ | Updated privacy policy draft in legal review; link placeholder in clients. |

## 9. Configuration (V12)

| Control | Status | Notes |
| --- | --- | --- |
| V12.1 Hardening guidelines | ✅ | Base images pinned; container hardening in `infra/kubernetes/backend/`. |
| V12.3 Dependency management | ✅ | Dependabot enabled; CI runs `pip-audit` and `npm audit --production`. |
| V12.4 Secure default configs | ✅ | `.env.example` avoids shipping secrets; defaults disable dangerous features. |
| V12.7 Infrastructure as Code | ✅ | Terraform modules enforce encryption, tagging, network rules. |

## 10. Summary & Actions

| Item | Owner | Target | Status |
| --- | --- | --- | --- |
| SEC-14: Add oauth2-proxy header signature validation & anomaly detection | Platform Eng | Week 5 | ⚠️ |
| SEC-21: Protect admin/probing endpoints behind RBAC & feature flags | Platform Eng | Week 6 | ⚠️ |
| SEC-09: Enforce MIME validation + malware scan for media uploads | Core Backend | Week 7 | ⚠️ |
| LEG-04: Finalize privacy policy copy and link in clients | Legal/PM | Week 4 | ⚠️ |
| OPS-07: Monitoring Agent alert transport implementation | SRE | Week 6 | ⚠️ |

- ✅ **Level 2 compliance** achievable post-mitigation of the above gaps.
- Review this checklist quarterly or after major architectural changes.
- Archive approved versions under `docs/security/archive/`.

