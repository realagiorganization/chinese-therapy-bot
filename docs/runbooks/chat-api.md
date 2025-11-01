# Runbook – Chat API Recovery

## Quick Reference
- **Purpose:** Restore FastAPI chat endpoints when streaming or turn processing degrades.
- **Primary Owners:** Backend team, CI Runner Agent.
- **Related Agents:** Monitoring Agent (alerts), Summary Scheduler Agent (downstream dependency).

## 1. Validate Incident Scope
1. Confirm alert details (Grafana / Application Insights) – capture request ID samples.
2. Check `services/backend/logs/chat` stream for elevated error rate or timeout.
3. Verify feature flags (`/api/features`) to ensure guardrails or experiments are not toggled off.

## 2. Immediate Mitigations
- **Feature Flag Rollback:** Disable experimental flags via `POST /api/features/{key}` (requires admin token).
- **Scale Out Backend:** Use `kubectl scale deployment chat-backend --replicas=<n>` if AKS cluster is healthy.
- **Restart Pod:** `kubectl rollout restart deployment chat-backend` to cycle pods after config changes.

## 3. Full Recovery
1. Run backend test suite locally or via GitHub Actions to ensure fixes compile: `services/backend> pytest -q`.
2. Deploy patched image using existing CI/CD workflow or manually `kubectl set image deployment/chat-backend chat-backend=<image>`.
3. Monitor Application Insights (latency/error dashboards) until metrics return to baseline.

## 4. Post-incident
- Update incident timeline in `docs/incidents/YYYY-MM-DD-<slug>.md`.
- File follow-up issues for root cause fixes and guardrail improvements.
