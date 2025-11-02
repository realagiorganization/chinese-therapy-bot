# MindWell Changelog

Document major product and infrastructure milestones for stakeholder visibility. Keep entries concise with deployment dates, version tags, and notable highlights.

## 2025-01-10 — v0.1.0 (Internal Alpha)
- Migrated chat orchestration to dual-provider LLM stack with streaming SSE support.
- Delivered therapist directory (web + mobile) with locale-aware filters and recommendation hints.
- Enabled conversation memory capture, daily/weekly summary agents, and analytics event pipeline.
- Rounded out authentication via SMS OTP + Google OAuth stubs backed by token rotation.
- Bootstrapped CI across backend/web/mobile and published infrastructure Terraform plans for AKS + AWS storage.

## 2025-01-17 — v0.1.1 (Agent Hardening)
- Added monitoring agent with Azure App Insights + AWS Cost Explorer guardrails and webhook alerts.
- Expanded regression test coverage (chat streaming, template service, retention automation, ASR endpoints).
- Documented infra/app release workflows plus mobile app store submission playbooks.
- Introduced agent lifecycle controller script for summary/data-sync/retention workers.
- Refreshed README/ENVS matrices to unblock new contributors and on-call rotations.

## 2025-01-24 — v0.1.2 (Experience Polish)
- Implemented Expo voice playback preferences, template quick-start chips, and offline transcript caching.
- Hardened therapist recommendations with embedding fallback, locale detection heuristics, and enriched metadata.
- Shipped server-side ASR API with graceful error surfacing for mobile/web clients.
- Tuned FastAPI lifespan wiring, added additional pytest suites, and verified Locust load scenarios.
- Updated documentation set (cost controls, investor brief, threat model) to align with current architecture.
