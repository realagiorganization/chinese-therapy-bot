# MindWell System Foundations

This document captures the Phase 0 deliverables: target architecture, deployment posture, and collaborative operations. It translates priorities from `DEV_PLAN.md` into actionable guidance for subsequent phases.

## Target Architecture Overview

```
┌─────────────────────┐
│     Mobile Apps      │
│  (iOS, Android, RN)  │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│   Web Client (SPA)   │
└─────────┬───────────┘
          │ GraphQL/REST
┌─────────▼───────────────────────────────────────┐
│            MindWell API Platform                │
│  - Gateway & Auth (FastAPI/NestJS)              │
│  - Chat Orchestrator & Streaming                │
│  - Therapist Services (directory, filters)      │
│  - Summary Scheduler & Agents                   │
└────┬────────┬────────────┬────────────┬────────┘
     │        │            │            │
┌────▼┐   ┌───▼───┐   ┌────▼────┐  ┌────▼───────┐
│ RDS │   │ Redis │   │ S3 Logs │  │ Agent Runs │
│/PGSQL│  │ Cache │   │Summaries│  │(ECS/Batch)│
└──┬──┘   └───┬───┘   └────┬────┘  └────┬───────┘
   │          │            │            │
┌──▼──────────▼────────────▼────────────▼────────┐
│                Observability Stack              │
│  (Azure Monitor, Grafana, Prometheus, Loki)     │
└────────────────────────────────────────────────┘
```

### Component Notes
- **Clients:** React Native powers mobile clients; a React SPA serves desktop browsers. Both rely on shared localization assets (Chinese-first) and stream responses via web sockets.
- **API Layer:** A modular service exposes REST/GraphQL endpoints, handling auth (oauth2-proxy email, demo codes, token renewal), therapist data, chat streaming, and report retrieval.
- **Intelligent Agents:** Four operational agents (CI Runner, Data Sync, Summary Scheduler, Monitoring) execute as containerized workers on Azure Container Apps or Kubernetes CronJobs/ScheduledJobs.
- **Data Stores:** Azure Database for PostgreSQL holds relational data. Azure Cache for Redis enables low-latency chat sessions and feature flags. Azure Blob Storage (S3-compatible API via AWS S3 for cross-cloud redundancy) retains raw transcripts, daily/weekly summaries, and media artifacts.
- **AI Integrations:** Primary inference uses Azure OpenAI (GPT-4o/4.1). AWS Bedrock (Claude/Sonnet) provides fallback capacity and specialized embeddings. Vector indices reside in Azure Cognitive Search.
- **Observability:** Azure Monitor routes metrics/logs to Grafana dashboards. Prometheus exporters capture application metrics; Loki centralizes structured logs. Alert rules feed PagerDuty and Teams/Slack.

## Cloud Deployment Decision
- **Primary Target:** Azure Kubernetes Service (AKS) with managed node pools (system + workload). Aligns with default stance in `DEV_PLAN.md`, leverages native integration with Azure OpenAI and managed PostgreSQL.
- **Rationale:**
  - Tight integration with Azure AD for secure therapist/admin tooling.
  - Simplified networking (Azure CNI + Application Gateway) and private endpoints for OpenAI/Database.
  - Consistent developer experience via `az` tooling and Terraform/Bicep support.
  - Supports hybrid needs (Windows nodepool option) if future therapy tooling uses .NET.
- **Secondary/Fallback:** AWS ECS Fargate for agent workloads and Bedrock access; S3 buckets remain authoritative for cross-region backup of conversation artifacts.

## Repository & CI/CD Operating Model
- **Repository Layout:** Monorepo hosting backend, web, mobile, infrastructure IaC, and docs. Each domain lives under `services/backend`, `clients/mobile`, `clients/web`, and `infra/`.
- **Branching Strategy:** Trunk-based with protected `main`. Feature work occurs on short-lived branches (`feature/<scope>`). Release candidates tag from `main` with semantic versioning (`vYYYY.Q.N`).
- **Environments:** `dev` (shared sandbox), `staging` (pre-production on AKS), `prod`. Feature branches may deploy ephemeral review environments using AKS namespaces.
- **CI/CD Workflow:** GitHub Actions triggered on PRs and merges.
  - **CI Runner Agent:** Builds backend containers, runs unit/integration tests, executes linting, and pushes images to Azure Container Registry.
  - **Mobile Pipeline:** Utilizes EAS or Fastlane runners to generate iOS TestFlight and Android beta builds; artifacts published to App Center.
  - **Infrastructure:** Terraform plan/apply jobs gated behind manual approval; secrets pulled via OIDC into Azure Key Vault.
  - **Deployments:** Argo CD (cluster-side) watches ACR tags and applies manifests/Helm charts. Rollbacks automated via `kubectl rollout undo` workflows.

## Next Steps
- Model component boundaries in a formal C4 diagram (Phase 1 dependency).
- Flesh out detailed IaC modules for AKS, PostgreSQL, and supporting services.
- Attach cost guardrails in Azure Cost Management with notification thresholds aligned to Monitoring Agent.
