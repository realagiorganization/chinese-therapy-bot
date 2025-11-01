# MindWell Support & Incident Response Playbook

This playbook operationalizes the DEV_PLAN requirement to establish customer support workflows and incident response procedures. It links the CI Runner, Data Sync, Summary Scheduler, and Monitoring agents described in `AGENTS.md` into a single escalation framework.

## 1. Support Intake

- **Channels**
  - `support@mindwell.dev` (primary)
  - In-app “Report an Issue” form (web + mobile) – posts to Zendesk queue `MindWell > Customer Support`.
  - Therapist partner hotline `+86-400-000-0000` (forwarding to Platform On-call outside business hours).
- **Triage Board** – Linear project `SUP` with templates for `Bug`, `Data Issue`, `Therapist Supply`, `Billing`.
- **SLA Targets**
  - P1: 15 min acknowledgment / 60 min mitigation plan.
  - P2: 1 h acknowledgment / 6 h mitigation.
  - P3: 4 h acknowledgment / 2 business-day resolution.

## 2. Severity Definitions

| Severity | Description | Examples | Primary Owner |
| --- | --- | --- | --- |
| **SEV-1** | Platform-wide outage or data loss impacting ≥50 % active users | Chat API unavailable, therapist directory empty, summaries missing | Monitoring Agent (incident commander) |
| **SEV-2** | Major feature degradation with workarounds | Streaming degraded to fallback, delays in summary generation >4 h | CI Runner Agent (rollbacks), Backend lead |
| **SEV-3** | Localized bugs or performance regressions | Voice input broken on Android, incorrect therapist badges | Feature squad owning area |
| **SEV-4** | Cosmetic defects / backlog items | Copy errors, minor UI glitches | Product design |

## 3. Roles & Responsibilities

- **Incident Commander (IC)** – Rotating Monitoring Agent member; responsible for communication, timeline, and declaring resolution.
- **Communications Lead** – Customer success liaison; posts updates to `#mindwell-status` Slack + Statuspage.
- **Operations Lead** – CI Runner Agent engineer; owns rollbacks, feature flag toggles, and verifying Terraform/infra impact.
- **Subject Matter Expert (SME)** – Functional owner (e.g., Backend lead, Mobile lead) providing diagnosis and fixes.

## 4. Workflow

1. **Detection**
   - Monitoring Agent alert, automated CI smoke test failure, or support ticket flagged P1/P2 triggers `#incidents` Slack channel creation via PagerDuty webhook.
2. **Declaration**
   - IC labels Linear issue as `incident`, assigns severity, records timeline start.
   - IC posts initial Statuspage entry (`Investigating`) within SLA.
3. **Stabilization**
   - Operations Lead evaluates rollback paths (`git revert`, feature flags via `/api/features`, or Terraform apply workflow) and executes safest fix-first option.
   - Data Sync / Summary Scheduler agents paused via `scripts/agent-control.sh` if they contribute to data churn.
4. **Communication Cadence**
   - SEV-1: every 15 min updates; SEV-2: every 30 min; SEV-3+: hourly or as needed.
   - Customer updates mirrored to email + Statuspage; internal notes maintained in Linear + incident doc (`docs/incidents/YYYY-MM-DD-<slug>.md`).
5. **Resolution & Verification**
   - IC confirms metrics normalized (latency, error rate, cost anomalies).
   - Operations Lead validates Terraform state matches expected (use `infra-apply` workflow in dry-run mode if drift suspected).
   - Communications Lead posts `Resolved` summary with timeline, impact, and follow-up tasks.
6. **Post-incident Review**
   - Within 48 h, hold 30 min retro. Capture root cause, contributing factors, detection gaps, and remediation tasks in incident doc.
   - Feed improvement items into DEV_PLAN backlog and assign owners.

## 5. On-call & Escalation Matrix

- **Primary** – Monitoring Agent engineer (rotating weekly).
- **Secondary** – Platform SRE (CI Runner Agent owner).
- **Escalations**
  1. Monitoring Agent → Platform SRE → CTO.
  2. For data integrity issues (therapist roster/summaries), escalate to Data Sync Agent owner.
  3. For customer-impacting AI behavior, loop in Responsible AI working group.

## 6. Tooling & Automation Hooks

- **PagerDuty** – Service `MindWell-Platform`, schedules mirrored in Google Calendar (`MindWell Oncall`).
- **Statuspage** – Component mapping (`Chat API`, `Therapist Data`, `Summaries`, `Mobile Notifications`).
- **Runbooks**
  - `docs/runbooks/chat-api.md` – Restart chat deployment, feature flag toggles.
  - `docs/runbooks/terraform.md` – Using plan/apply workflows, drift detection.
  - `docs/runbooks/data-sync.md` – Handling stuck S3 ingestion or malformed therapist payloads.

## 7. Customer Communication Templates

- **Initial Incident Notification**
  ```
  Subject: [MindWell] Incident Update – {component}

  We are investigating an issue affecting {scope}. Our team identified {symptom} at {timestamp TZ}. Expect next update within {cadence}.
  ```
- **Resolution**
  ```
  Subject: [MindWell] Incident Resolved – {component}

  The issue affecting {scope} has been resolved as of {timestamp TZ}. Root cause: {summary}. We are implementing {action items} to prevent recurrence.
  ```

## 8. Continuous Improvement Checklist

- Quarterly incident drill (tabletop) covering SEV-1 and SEV-2 scenarios.
- Monthly review of alert thresholds with Finance (cost) and Clinical leads (therapist availability).
- Update on-call roster and escalation contacts in `ENVS.md` whenever Terraform variables change.
- Ensure Monitoring Agent dashboards include latest guardrail metrics (latency, error budgets, cloud spending).
