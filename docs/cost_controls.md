# Cost Controls & Budgeting

This document outlines the current cost assumptions and guardrails for the MindWell platform. Estimates reference the default Terraform sizing (East Asia for Azure, ap-northeast-1 for AWS) and typical early-access usage patterns. All amounts are shown in USD unless noted.

## 1. Baseline Monthly Infrastructure Model

### 1.1 Azure Core Platform (East Asia)
| Resource | Qty / Assumption | Unit Cost* | Est. Monthly | Notes |
| --- | --- | --- | --- | --- |
| AKS system node pool (Standard_D4ds_v5) | 2 nodes x 730 h | $0.31 / h | **$452.60** | Linux pricing; covers control-plane add-ons. |
| AKS workload node pool (Standard_D8ds_v5) | 3 node avg x 730 h | $0.62 / h | **$1,357.80** | Autoscale floor is 2; each extra node ~ $452.60 / month. |
| Azure Database for PostgreSQL Flexible Server (GP Ddsv5, 4 vCore) | 730 h | $0.538 / h | **$392.74** | Includes zone redundant HA. |
| Postgres storage | 128 GiB | $0.12 / GiB-month | **$15.36** | Additional backup storage above 128 GiB billed at $0.095 / GiB-month. |
| Log Analytics + App Insights ingestion | 30 GiB / month | $2.88 / GiB | **$86.40** | Add ~$2.88 for every extra GiB of telemetry. |
| Bandwidth egress (Internet) | 0.5 TiB / month | $0.087 / GiB | **$43.50** | Assumes CDN offload covers static assets. |
| Azure Key Vault operations | 100k ops | $0.03 / 10k ops | **$0.30** | Access via CSI driver + automation agents. |
| Cognitive Services Speech (ASR + TTS) | 40k standard minutes | ~$1.00 / 1k min | **$40.00** | Mix of transcription + neural TTS workloads. |
| **Azure subtotal** |  |  | **~ $2,388** |  |

\*Pricing pulled from Azure Retail Prices API (May 2025) and rounded to two decimals.

### 1.2 AWS Storage & Transfer (ap-northeast-1)
| Resource | Qty / Assumption | Unit Cost | Est. Monthly | Notes |
| --- | --- | --- | --- | --- |
| S3 conversation logs bucket | 200 GiB hot tier | $0.023 / GiB-month | **$4.60** | Lifecycle rules move data to Standard-IA after 30 days. |
| Standard-IA transcripts (cold tier) | 120 GiB | $0.0125 / GiB-month | **$1.50** | Retrieval overruns billed separately (~$0.01 / GiB). |
| S3 summaries bucket | 50 GiB | $0.023 / GiB-month | **$1.15** | Retains 24 months of JSON payloads. |
| S3 media bucket | 100 GiB | $0.023 / GiB-month | **$2.30** | Therapist media + marketing assets. |
| S3 request charges | 1.2 M PUT/LIST, 2.0 M GET | $0.005 / 1k (PUT) | **$10.00** | Includes lifecycle transitions and agent imports. |
| Data transfer out to Internet | 200 GiB | $0.09 / GiB | **$18.00** | Media + transcript API responses. |
| **AWS subtotal** |  |  | **~ $37** |  |

**Combined base infrastructure:** ~ **$2,425 / month** before LLM usage and contingency buffers. Applying a 20% reserve for bursty workloads yields a planning budget of **$2,910 / month**.

## 2. LLM Usage Cost Scenarios

Assumptions:
- Primary chat + summarisation provider: **Azure OpenAI GPT-4o mini** (input $0.0006 / 1k tokens, output $0.0024 / 1k tokens).
- Fallback to **AWS Bedrock Claude 3 Haiku** (input $0.00025 / 1k, output $0.00125 / 1k) for transient Azure outages.
- Last-resort OpenAI `gpt-3.5-turbo` (input $0.0005 / 1k, output $0.0015 / 1k) for local debugging or when both Azure/AWS are degraded.
- Daily summaries consume 1.5k in / 0.6k out tokens in testing and 1.6k / 0.7k in production. Weekly summaries consume 2.0k in / 0.8k out tokens in testing and 2.2k / 0.9k in production.
- Month = 30 days; production weekly summaries computed for four weeks.

| Scenario | Monthly Token Volume (Input / Output) | Azure GPT-4o mini | Bedrock Claude 3 Haiku | OpenAI gpt-3.5-turbo | Monthly Total |
| --- | --- | --- | --- | --- | --- |
| Testing (50 DAU, 8 turns) | 8.65 M / 5.86 M | $18.10 | $0.47 | $0.13 | **$18.70** |
| Production (1k DAU, 12 turns) | 311.8 M / 215.1 M | $612.28 | $19.71 | $9.05 | **$641.03** |

- Every additional 100k chat turns at production token density adds ~ **$27.4** if handled entirely by Azure OpenAI.
- Monitoring Agent should alarm if monthly LLM cost accrual exceeds 75% of the forecast before day 20 of the billing cycle.

## 3. Tooling & Licensing

| Tool / Service | Seats | Rate | Monthly Cost | Budget Owner |
| --- | --- | --- | --- | --- |
| Claude Code Mirror | 3 engineering seats | CNY 162 / seat-month (~$22.50) | **$67.50** | Engineering Productivity (Platform team) |

- Annual renewal handled via Finance Ops; charge back to cost center `PLAT-ENG-TOOLS`.
- Seat allocations reviewed quarterly; Monitoring Agent flags unused entitlements for reclamation.

## 4. Budget Guardrails & Alerts

- **Azure Cost Guardrail:** Set `monthly_cost_budget_amount` to **$3,000** in Terraform for production. Existing policy emits alerts at 80% and 95%; add a Monitoring Agent webhook that creates an Opsgenie low-priority incident at 95% and escalates to Finance if spend exceeds 105%.
- **AWS Budgets:** Create matching AWS Budgets (`mindwell-core-prod`) with thresholds at 70% (email), 90% (Slack alert), 100% (PagerDuty to Platform on-call). Leverage cost allocation tags mirroring Terraform `default_tags`.
- **LLM Quota Alerts:** Enable Azure OpenAI quota notifications for the GPT-4o mini deployment at 60% tokens, 90% tokens, and configure Monitoring Agent to shed optional requests (explore page personalization) once 90% threshold is hit.
- **Data Transfer Watch:** Monitoring Agent tracks CDN and S3 egress. If combined daily egress exceeds 25 GiB for three consecutive days, trigger a cost investigation task.
- **ASR/TTS Usage:** Azure Speech metrics with 50k minute soft cap; send alert at 40k minutes to evaluate caching or batching strategies.

## 5. Next Actions

1. Populate Terraform `dev.tfvars` / environment-specific tfvars with the budget amount (`monthly_cost_budget_amount = 3000`) and stakeholder emails (`cost_budget_contact_emails`).
2. Configure AWS Budgets via IaC or console (owner: Platform Engineering, due before pilot launch).
3. Feed monthly actuals into Finance dashboards; compare against the **$2,910** infrastructure + **$641** LLM production baseline to refine forecasts after the first pilot cohort.

**Revision owner:** Platform Engineering. Update this document whenever Terraform sizing, traffic assumptions, or provider pricing changes.
