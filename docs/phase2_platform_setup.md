# Phase 2 – Platform & Infrastructure Setup

This document records the baseline infrastructure design for Phase 2 of the MindWell rollout. It complements the Terraform configuration under `infra/terraform/environments/dev` and maps directly to the Phase 2 checklist in `PROGRESS.md`.

## 1. Azure Kubernetes Service (AKS)
- **Cluster** – Single regional AKS cluster (`SystemAssigned` identity, Azure CNI) with dedicated system and workload node pools.
- **Networking** – VNet `10.20.0.0/16` (sample) split into system (`/24`) and workload (`/24`) subnets plus a delegated subnet for PostgreSQL.
- **Security** – API server locked down via IP allowlist, Azure AD RBAC enabled with admin group injection, OIDC issuer + workload identity for GitHub Actions and agents.
- **Observability** – Diagnostic settings ship control plane logs/metrics to Log Analytics. Autoscaler surge set to `33%` for zero-downtime upgrades.

## 2. Data Stores
- **PostgreSQL Flexible Server** – Zone redundant deployment, private networking via delegated subnet + private DNS zone. Daily backups (14-day retention) with geo-redundant storage.
- **Object Storage** – Three S3 buckets segmented by classification:
  - `conversation-logs` (sensitive transcripts, KMS encryption, versioned)
  - `summaries` (daily/weekly outputs, KMS + versioning)
  - `media` (therapist assets, AES256, selectively shareable)
- **Secrets** – Azure Key Vault stores platform credentials (e.g., Postgres admin password). AWS Secrets Manager mirrors the OpenAI key for workloads running in AWS.

## 3. IAM & Access Control
- **CI Runner Role** – IAM role granting scoped read/write to S3 buckets for CI/CD, automation agents, and cross-cloud sync jobs.
- **Key Vault Policies** – Admin object ID granted full control; AKS kubelet identity and cluster managed identity both receive `Key Vault Secrets User` for CSI driver and GitHub OIDC workloads (see Terraform outputs for IDs).
- **Network ACLs** – Key Vault restricted to explicit IP ranges. S3 buckets block public access (media bucket allows object-level ACLs for shareable assets).

## 4. Observability & Cost Guardrails
- **Log Analytics Workspace** – Central ingestion point for AKS, agents, and custom app logs (30-day retention default, configurable).
- **Application Insights** – Workspace-based component enables distributed tracing, request/failure metrics, and dependency insights for FastAPI services.
- **Azure Dashboard** – Terraform-rendered dashboard surfaces environment metadata plus App Insights request/failure charts for quick triage.
- **Metric Alerts** – AKS node CPU alert and AppTraces error-rate scheduled query route to the shared on-call action group (email + SMS).
- **Cost Budget** – Subscription-level monthly budget with 80% and 95% thresholds notifying the platform + finance distro.

## 5. Deployment Workflow Alignment
- Terraform can be executed locally or via GitHub Actions runners with OIDC federation.
  - Local operators can run `infra/scripts/run_terraform_plan.sh <env>` after copying `infra/terraform/dev.tfvars.example` to a real tfvars file and exporting cloud credentials.
  - GitHub Actions workflow `.github/workflows/infra-plan.yml` performs a non-destructive plan using OIDC to Azure/AWS once repository secrets are configured (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AWS_TERRAFORM_ROLE_ARN`, etc.).
- Remote backend (Azure Storage) is recommended before collaborating; block is stubbed for later wiring (`TF_BACKEND_CONFIG_FILE` can be passed to the helper script or workflow as soon as the backend exists).
- Placeholder secrets and credentials defined as variables to avoid baking sensitive data into state files. Workflow-generated tfvars source sensitive values from repository secrets.

## 6. Outstanding Work & Assumptions
- Apply operations have **not** been run yet; cloud resources remain to be provisioned.
- Production-grade setup will introduce additional node pools (GPU/inference) and dedicated subnets for private endpoints (OpenAI, Redis, etc.).
- AWS IAM access patterns for Data Sync/Summary Scheduler agents will be expanded when their execution environments are finalized.
- Observability dashboards currently focus on infrastructure; deep-dive workbooks (latency percentiles, conversation-level KPIs) will follow after service deployment.
- Cost budget thresholds assume USD billing; revisit amounts when accurate Azure pricing projections are finalized.
- Workload identity still requires an end-to-end dry run. A validation job manifest now lives in `infra/kubernetes/samples/workload-identity-validation.yaml` to exercise Key Vault access once the cluster is online.

## 7. Terraform Implementation Snapshot
- **Source:** `infra/terraform/`
- **Key Files:** `azure_core.tf`, `azure_aks.tf`, `azure_postgres.tf`, `azure_keyvault.tf`, `aws_storage.tf`, `observability.tf`, `secrets.tf`.
- **Runtime Manifests:** `infra/kubernetes/backend/` hosts the base Kustomize overlay that mounts Key Vault secrets via the CSI driver and annotates the backend service account for workload identity. The `infra/kubernetes/samples/` folder adds a Key Vault retrieval job for quick validation.
- **Highlights:** AKS workload identity enabled; PostgreSQL admin password seeded to Key Vault; three S3 buckets with encryption/versioning; CI Runner Agent IAM role; App Insights + AKS CPU & error alerts; Azure Portal dashboard and cost budget notifications.
- **Next Steps:** Wire Terraform remote state, add database migration module, extend monitoring dashboards (Grafana/Workbook) once application metrics are defined, and automate apply stages with manual approval.
