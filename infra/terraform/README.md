# MindWell Terraform Infrastructure

This configuration captures the **Phase 2 – Platform & Infrastructure Setup** scope outlined in `PROGRESS.md` and `DEV_PLAN.md`. It codifies the baseline Azure and AWS resources required to stand up the MindWell platform.

## What’s Included

- Azure resource group, virtual network, and subnets with delegated networking for PostgreSQL.
- Azure Kubernetes Service (AKS) cluster with workload identity, Log Analytics integration, and user node pool autoscaling.
- Azure Database for PostgreSQL Flexible Server (zone redundant) and secret bootstrap via Key Vault.
- Azure Application Insights (workspace-based) plus Azure Portal dashboard and workbook-friendly metrics for runtime observability.
- Azure Key Vault with RBAC, soft-delete, and secret seeding for the database administrator password.
- AWS VPC with segmented public/private subnets to host cross-cloud services.
- AWS S3 buckets for conversation logs, summaries, and therapist media with encryption, versioning, and IAM role for the CI Runner Agent.
- AWS RDS for PostgreSQL (optional replica / analytics workload) with Secrets Manager credential seeding.
- AWS EC2 automation agent (for Data Sync / Summary Scheduler workloads) with hardened security groups.
- AWS Secrets Manager placeholders for model credentials and agent integrations.
- Azure Monitor action group, AKS CPU alert, application error-rate scheduled query alert, and Azure cost budget notifications for spend visibility.

## Usage

1. Copy `backend.hcl.example` to `backend.hcl` and populate the Azure Storage account details that will hold the state file. The Terraform service principal must have at least **Storage Blob Data Contributor** access to the storage account.
2. Create a `terraform.tfvars` (or environment-specific `*.tfvars`) file with required values:

```hcl
environment                     = "dev"
azure_subscription_id           = "00000000-0000-0000-0000-000000000000"
azure_tenant_id                 = "11111111-1111-1111-1111-111111111111"
aws_account_id                  = "222222222222"
aws_region                      = "ap-northeast-1"
aws_vpc_cidr                    = "10.60.0.0/16"
aws_private_subnet_cidrs        = ["10.60.1.0/24", "10.60.2.0/24"]
aws_public_subnet_cidr          = "10.60.10.0/24"
s3_logs_bucket_name             = "mindwell-dev-conversation-logs"
s3_summaries_bucket_name        = "mindwell-dev-summaries"
s3_media_bucket_name            = "mindwell-dev-media"
aws_rds_instance_class          = "db.t4g.medium"
aws_rds_database_name           = "mindwell"
aws_rds_master_username         = "mindwellapp"
aws_agent_instance_type         = "t3.medium"
aws_agent_allowed_ssh_cidrs     = ["203.0.113.0/24"]
application_insights_name       = "appi-mindwell-dev"
monthly_cost_budget_amount      = 200
cost_budget_start_date          = "2025-01-01"
cost_budget_end_date            = "2025-12-31"
cost_budget_contact_emails      = ["finance@mindwell.dev", "platform@mindwell.dev"]
key_vault_admin_object_ids      = ["33333333-3333-3333-3333-333333333333"]
oidc_github_workload_client_id  = "00000000-0000-0000-0000-000000000000"
```

3. Initialize and plan the deployment:

```bash
terraform init -backend-config=backend.hcl
terraform plan -var-file=dev.tfvars
```

> 💡 **Remote State:** Alternatively, pass `-backend-config` flags directly in CI/CD if injecting secrets through environment variables.

## Notes & Next Steps

- Subnet CIDRs and resource names are parameterized to support future staging/prod environments.
- Additional node pools (GPU/inference) and workbook visualizations can be layered as Phase 2 progresses.
- Secrets Manager secrets are placeholders; populate key/value pairs via CI/CD once the real credentials exist. The RDS password is stored automatically under `mindwell/<env>/rds/postgres`.
- Firewall/IP allowlists should be refined once corporate network ranges are finalized.
- S3 lifecycle policies now:
  - Transition conversation transcripts in `conversations/` to Standard-IA after 30 days, Glacier after 90 days, and purge after 1 year.
- Transition daily/weekly summaries in `summaries/` to Standard-IA after 60 days, Glacier after 180 days, with a 2 year retention window.
- Expire media uploads after 365 days and automatically clean up incomplete multipart uploads after 7 days.
- EC2 automation agents default to SSH open to the internet for local development convenience; restrict `aws_agent_allowed_ssh_cidrs` for production usage or integrate with Session Manager.
