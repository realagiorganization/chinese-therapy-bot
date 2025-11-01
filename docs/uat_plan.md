# MindWell Pilot UAT Plan

This plan outlines how we will recruit pilot users, execute user acceptance testing (UAT),
and capture feedback to close Phase 6 of the development roadmap.

## 1. Objectives

- Validate the end-to-end therapy companion experience across web and mobile clients.
- Ensure therapist recommendations, summaries, and journey dashboards match expectations.
- Observe performance/stability on target devices (iPhone 12/SE, Redmi Note 11, Pixel 6a).
- Capture qualitative feedback on tone, trust, and therapist matching accuracy.
- Derive prioritized backlog items for Phase 7 deployment readiness.

## 2. Pilot Cohort

| Persona | Count | Recruitment Channel | Notes |
| --- | --- | --- | --- |
| Urban professionals (25–40) | 6 | Existing therapist network referrals | Focus on stress/anxiety management flows. |
| University students (18–24) | 4 | Student counseling partners | Evaluate language tone and affordability messaging. |
| Therapists | 3 | MindWell therapist advisors | Validate therapist showcase, onboarding, and recommendation rationales. |

- Target **13 participants** with signed pilot NDAs (template in `docs/legal/nda_pilot.md`).
- Incentives: ¥300 gift card or 1-hour therapist consultation.

## 3. Test Scenarios

1. **Onboarding & Authentication**
   - SMS OTP enrollment (primary), Google OAuth (secondary).
   - Device hand-off: login web → mobile; verify session continuity.
2. **Chat Experience**
   - Start a new session; observe voice input (browser + mobile).
   - Trigger therapist recommendations; inspect memory highlights.
   - Submit at least two daily summaries; verify weekly roll-up.
3. **Therapist Directory & Detail**
   - Filter by specialty, language, price.
   - Open detail view, review recommendation badges and rationale copy.
4. **Journey Dashboard**
   - Review 10-day daily and 10-week weekly lists.
   - Inspect spotlight + transcript tabs; confirm offline caching on mobile.
5. **Explore Module**
   - Toggle feature flags (via QA environment) to validate staged rollouts.
6. **Notifications & Offline**
   - Enable push notifications; trigger summary ready alert via Summary Scheduler.
   - Kill app/network; reopen to confirm cached transcript restore.

## 4. Schedule & Tooling

- **Week 4 Day 1–2:** Recruit cohort, ship onboarding emails (template `docs/communications/pilot_welcome.md`).
- **Week 4 Day 3:** Kickoff briefing (30 minutes) covering expectations & support channel.
- **Week 4 Day 3–7:** UAT window (5 days) with daily check-in Slack thread `#pilot-uat`.
- **Week 4 Day 8:** Debrief synthesis workshop (product + therapists + engineering).
- Tooling:
  - **Feedback capture:** Linear board `UAT-2025` with issue templates (bug, UX, suggestion).
  - **Session recordings:** Optional FullStory in web pilot environment; disable PII capture per `docs/data_governance.md`.
  - **Surveys:** Post-session Google Form capturing satisfaction, trust score, feature gaps.

## 5. Success Criteria

- ≥ 80% of participants report the assistant tone as "supportive" or "very supportive".
- ≥ 70% of participants find at least one therapist recommendation relevant.
- Critical bug count ≤ 3; all blockers resolved or mitigated before promoting to Phase 7.
- Performance: median API latency < 1.5s; mobile cold start < 3.5s on Redmi Note 11.

## 6. Roles & Responsibilities

| Role | Owner | Responsibilities |
| --- | --- | --- |
| Pilot Lead | Product Manager | Recruitment, communications, schedule management. |
| QA Lead | QA Engineer | Scenario scripts, bug triage, reproduction, and validation. |
| Therapist Liaison | Clinical Ops | Coordinate therapist advisors and scenario reviews. |
| Engineering Support | Backend + Frontend Leads | Triage technical issues, deploy hotfixes, instrument telemetry. |
| Monitoring Agent | SRE | Track latency, error rate, and cost guardrails during pilot. |

## 7. Reporting

- Daily digest in `#pilot-uat` summarizing new issues, resolved items, telemetry anomalies.
- Post-pilot report stored at `docs/reports/uat/<YYYY-MM-DD>-pilot-summary.md` with:
  - Participant feedback themes
  - Metrics vs success criteria
  - Backlog recommendations tagged by severity/effort

## 8. Next Steps

1. Finalize recruitment list and send invites (Owner: Product, Due: Week 4 Day 1).
2. Prepare pilot environment (feature flags, summary scheduling frequency).
3. Configure Monitoring Agent thresholds specific to pilot traffic (error rate 5%, latency 1.5s).
4. Publish bug triage SLA (critical: 12h, high: 24h, medium: 72h).

Update this document as the pilot progresses; archive the final version with outcomes appended.

