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
- **Key Vault Policies** – Admin object ID granted full control; AKS kubelet identity granted `Get` for pulling secrets through CSI driver.
- **Network ACLs** – Key Vault restricted to explicit IP ranges. S3 buckets block public access (media bucket allows object-level ACLs for shareable assets).

## 4. Observability & Cost Guardrails
- **Log Analytics Workspace** – Central ingestion point for AKS, agents, and custom app logs (30-day retention default, configurable).
- **Azure Dashboard** – Terraform-rendered dashboard visualizes API server traffic and node CPU trending for the selected environment.
- **Metric Alert** – AKS node CPU alert paged to on-call action group (email + SMS). Additional rules can reuse the same action group.

## 5. Deployment Workflow Alignment
- Terraform can be executed locally or via GitHub Actions runners with OIDC federation.
- Remote backend (Azure Storage) is recommended before collaborating; block is stubbed for later wiring.
- Placeholder secrets and credentials defined as variables to avoid baking sensitive data into state files.

## 6. Outstanding Work & Assumptions
- Apply operations have **not** been run yet; cloud resources remain to be provisioned.
- Production-grade setup will introduce additional node pools (GPU/inference) and dedicated subnets for private endpoints (OpenAI, Redis, etc.).
- AWS IAM access patterns for Data Sync/Summary Scheduler agents will be expanded when their execution environments are finalized.
- Observability dashboards currently focus on infrastructure; app-level SLO dashboards (latency, error rate, cost) will follow after service deployment.
- Azure Cost Management alerts require an enterprise agreement scope; placeholders will be added after subscription details are confirmed.

