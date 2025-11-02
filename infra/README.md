# MindWell Infrastructure

This directory holds infrastructure-as-code artifacts for provisioning MindWell's hybrid Azure and AWS footprint. Phase 2 focuses on foundational services required for the chatbot, therapist agents, and data pipelines.

## Layout

```
infra/
  terraform/
    providers.tf        # Provider requirements for Azure + AWS
    variables.tf        # Input variables (shared across environments)
    locals.tf           # Naming helpers and default tags
    azure_core.tf       # Resource group, virtual network, subnets, Log Analytics
    azure_aks.tf        # AKS cluster + workload node pool + federated identity
    azure_postgres.tf   # Azure Database for PostgreSQL Flexible Server
    azure_keyvault.tf   # RBAC-enabled Key Vault with seeded secrets
    aws_storage.tf      # Conversation logs / summaries / media buckets + IAM role
    secrets.tf          # AWS Secrets Manager placeholders for agents
    observability.tf    # Monitor action group and AKS CPU alert
    outputs.tf          # Handy outputs for downstream automation
    README.md           # Usage instructions and tfvars example
```

Create environment-specific `*.tfvars` files at the root of `infra/terraform/` (e.g., `dev.tfvars`, `staging.tfvars`). Terraform workspaces or wrapper scripts can select the desired variable set during deployment.

## Usage

1. Export or provide credentials for Azure (Service Principal / Managed Identity) and AWS (access keys or SSO).
2. Create a `terraform.tfvars` file under `environments/dev/` with project-specific values (sample below).
3. Initialize and plan:

```bash
cd infra/terraform
terraform init
terraform plan -var-file=dev.tfvars -out dev.tfplan
```

4. Apply once the plan is reviewed:

```bash
terraform apply dev.tfplan
```

### Sample `terraform.tfvars`

```hcl
environment                    = "dev"
azure_subscription_id          = "00000000-0000-0000-0000-000000000000"
azure_tenant_id                = "00000000-0000-0000-0000-000000000000"
azure_location                 = "eastasia"
aws_account_id                 = "111111111111"
aws_region                     = "ap-northeast-1"
s3_logs_bucket_name            = "mindwell-dev-conversation-logs"
s3_summaries_bucket_name       = "mindwell-dev-summaries"
s3_media_bucket_name           = "mindwell-dev-media"
aks_kubernetes_version         = "1.29.4"
aks_system_node_count          = 2
aks_workload_node_count        = 3
key_vault_admin_object_ids     = ["22222222-2222-2222-2222-222222222222"]
oidc_github_workload_client_id = "33333333-3333-3333-3333-333333333333"
tags = {
  owner       = "platform"
  cost_center = "mindwell-core"
}
```

### Notes
- Enable an Azure Storage Account backend for Terraform state before multi-user usage.
- Configure Azure Key Vault firewall rules to include GitHub Action runner egress IPs when running in CI.
- Populate secret values (OpenAI, SMS, Bedrock) via AWS Secrets Manager once credentials are provisioned.
