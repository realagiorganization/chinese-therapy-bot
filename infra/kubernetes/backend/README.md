# MindWell Backend Kustomize Overlay

This overlay demonstrates how the FastAPI backend consumes secrets from Azure Key Vault via the Secrets Store CSI driver.

## Files

- `secretproviderclass.yaml` – Maps Key Vault secrets (`postgres-admin-password`, `database-url`, `openai-api-key`, `sms-provider-api-key`, `app-insights-api-key`, `alert-webhook-url`, `aws-access-key-id`, `aws-secret-access-key`) into the `mindwell-backend` Kubernetes secret.
- `deployment.yaml` – Annotates the service account for Azure workload identity, mounts the CSI volume, and sources environment variables from the projected secret.
- `service.yaml` – Internal ClusterIP service for the API pods.
- `kustomization.yaml` – Applies the resources into the `mindwell` namespace.

## Usage

1. Export substitution values prior to applying:

```bash
export AKS_MANAGED_IDENTITY_CLIENT_ID=<client-id-from-terraform-output>
export AZURE_KEY_VAULT_NAME=kv-mindwell-dev
export AZURE_TENANT_ID=<tenant-id>
export BACKEND_IMAGE=ghcr.io/realagiorganization/mindwell-backend:dev
```

2. Render the manifests:

```bash
kustomize build infra/kubernetes/backend
```

3. Deploy to the cluster:

```bash
kustomize build infra/kubernetes/backend | kubectl apply -f -
```

> The Secrets Store CSI driver and Azure identity webhook must already be installed on the AKS cluster. Terraform role assignments (`Key Vault Secrets User`) ensure the kubelet and workload identities can fetch the referenced secrets.
