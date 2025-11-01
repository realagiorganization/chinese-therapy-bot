# Phase 2 - Secret Management & Rotation

This document closes the outstanding **Phase 2** checklist items around secret governance. It explains how Azure Key Vault, AWS Secrets Manager, and the AKS secret store CSI driver collaborate to supply credentials to MindWell services while enabling regular rotation.

## 1. Source of Truth

- **Azure Key Vault (`kv-mindwell-<env>`):** Authoritative store for application runtime secrets consumed by workloads on AKS (database credentials, JWT signing keys, LLM API keys mirrored from AWS).
- **AWS Secrets Manager (`mindwell/<env>/...`):** Holds upstream credentials managed by third parties (OpenAI, Bedrock, SMS provider). Replicated into Key Vault via the Data Sync agent and rotation automation.
- **Terraform Outputs:** `aks_managed_identity_client_id`, `aks_managed_identity_principal_id`, and `aks_kubelet_identity_object_id` expose the identities that require secret access and feed CI/CD automation.

## 2. Access Model

1. **AKS Workloads:** The kubelet managed identity receives the `Key Vault Secrets User` role on the vault. Pods mount secrets with the Azure Key Vault provider via the `SecretProviderClass` defined in `infra/kubernetes/backend/secretproviderclass.yaml`.
2. **GitHub Actions:** Workload identity federation uses the cluster managed identity (`aks_managed_identity_client_id`) so CI pipelines can preflight Helm releases without storing long-lived credentials.
3. **Operational Staff:** Administrative Azure AD object IDs are provisioned through `var.key_vault_admin_object_ids` with the `Key Vault Administrator` role.

## 3. Rotation Workflows

| Secret Category | Store of Record | Rotation Cadence | Automation Hook |
| --- | --- | --- | --- |
| LLM keys (OpenAI, Bedrock) | AWS Secrets Manager | 45 days | GitHub Actions workflow `llm-key-rotation.yml` (to be authored) fetches new keys, updates AWS Secret, then syncs to Key Vault via Data Sync agent job `agents/data_sync.py`. |
| Database password | Azure Key Vault | 90 days | Terraform rotates the initial password. Ongoing rotations use `az postgres flexible-server` CLI automation invoked by the CI Runner agent, writing back to the `postgres-admin-password` secret. |
| SMS provider token | AWS Secrets Manager | 60 days | Provider self-service portal resets token; automation script updates the secret and triggers Data Sync agent to refresh Key Vault copy. |
| JWT signing keys | Azure Key Vault | 180 days | Manual approval runbook using `az keyvault key rotate` plus Helm release to restart backend pods. |

> **Alerting:** Monitoring Agent watches Key Vault near-expiry events (7-day lookahead) and posts to the on-call Slack channel.

## 4. Implementation Checklist

- [x] Terraform grants `Key Vault Secrets User` to AKS managed identities (`azure_keyvault.tf`).
- [x] Terraform outputs publish managed identity IDs required for GitHub OIDC federation (`outputs.tf`).
- [x] Kubernetes manifests consume Key Vault secrets through the CSI driver (`infra/kubernetes/backend/`).
- [ ] Author GitHub Actions workflows for automated LLM credential rotation.
- [ ] Wire Data Sync agent to mirror rotated secrets from AWS to Azure.

## 5. Runbook Snippets

**Manual Secret Sync (temporary measure)**

```bash
aws secretsmanager get-secret-value \
  --secret-id mindwell/dev/openai/api-key \
  --query SecretString --output text |
az keyvault secret set \
  --vault-name kv-mindwell-dev \
  --name openai-api-key \
  --value @-
```

**Validating Pod Access**

```bash
kubectl get secrets mindwell-backend --namespace mindwell \
  -o jsonpath='{.data.OPENAI__API_KEY}' | base64 --decode
```

If the result is empty or errors, check the role assignments created in Terraform.
