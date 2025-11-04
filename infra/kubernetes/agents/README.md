# MindWell Automation Agents (Kubernetes Overlay)

This overlay provisions CronJobs for the automation agents described in `AGENTS.md`:

- **Data Sync Agent** (`mindwell-data-sync`) — normalises therapist datasets and uploads locale-specific payloads to S3 every 4 hours.
- **Summary Scheduler Agent** (`mindwell-summary-scheduler`) — generates daily and weekly summaries once per day.
- **Monitoring Agent** (`mindwell-monitoring-agent`) — polls observability backends every 5 minutes and dispatches alerts when guardrails are breached.

The manifests assume the **backend overlay** has already been applied so that:

1. The `backend-secrets` `SecretProviderClass` exists and can project Azure Key Vault secrets into the `mindwell-backend` secret.
2. The container image published at `BACKEND_IMAGE` bundles the CLI entry points exposed in `services/backend/pyproject.toml`.

## Configuration

1. Update `configmap.yaml` with environment-specific values (buckets, thresholds, alert channel, etc.). The committed values are placeholders to highlight the required keys.
2. Export the same substitution variables used by the backend overlay before rendering:

```bash
export AKS_MANAGED_IDENTITY_CLIENT_ID="<aks-managed-identity-client-id>"
export AZURE_KEY_VAULT_NAME="kv-mindwell-dev"
export AZURE_TENANT_ID="<azure-tenant-id>"
export BACKEND_IMAGE="ghcr.io/realagiorganization/mindwell-backend:dev"
```

If you prefer to avoid editing the tracked ConfigMap, create an environment-specific `kustomization.patch.yaml` that overrides the literals or use `kustomize edit` to inject the runtime values.

## Usage

Render the manifests:

```bash
kustomize build infra/kubernetes/agents
```

Apply to the cluster:

```bash
kustomize build infra/kubernetes/agents | kubectl apply -f -
```

The CronJobs mount the same CSI-backed secret volume as the backend Deployment to hydrate the `mindwell-backend` secret and pull secrets such as:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `SMS_PROVIDER_API_KEY`
- `APP_INSIGHTS_API_KEY`
- `ALERT_WEBHOOK_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Ensure the corresponding Key Vault entries exist before rolling out the agents. The Data Sync agent writes ingestion metrics to `DATA_SYNC_METRICS_PATH` and the Monitoring agent stores JSON metrics snapshots under `MONITORING_METRICS_PATH`; by default both persist to ephemeral directories inside the pod. Attach a persistent volume if historical retention is required.
