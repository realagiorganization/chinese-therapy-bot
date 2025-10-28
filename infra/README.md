# MindWell Infrastructure

This directory holds infrastructure-as-code artifacts for provisioning MindWell's hybrid Azure and AWS footprint. Phase 2 focuses on foundational services required for the chatbot, therapist agents, and data pipelines.

## Layout

```
infra/
  terraform/
    environments/
      dev/
        main.tf         # Azure + AWS resources for the dev environment
        variables.tf    # Input variables for the dev stack
        outputs.tf      # Useful outputs (AKS ID, Postgres FQDN, bucket names)
        templates/
          azure_dashboard.json.tftpl  # Observability dashboard definition
```

Additional environments (`staging/`, `prod/`) can reuse the same module patterns with environment-specific variable files.

## Usage

1. Export or provide credentials for Azure (Service Principal / Managed Identity) and AWS (access keys or SSO).
2. Create a `terraform.tfvars` file under `environments/dev/` with project-specific values (sample below).
3. Initialize and plan:

```bash
cd infra/terraform/environments/dev
terraform init
terraform plan -out plan.tfplan
```

4. Apply once the plan is reviewed:

```bash
terraform apply plan.tfplan
```

### Sample `terraform.tfvars`

```hcl
project_name                   = "MindWell"
environment                    = "dev"
azure_subscription_id          = "00000000-0000-0000-0000-000000000000"
azure_tenant_id                = "00000000-0000-0000-0000-000000000000"
azure_location                 = "eastasia"
aws_region                     = "ap-northeast-1"
aws_access_key                 = "REDACTED"
aws_secret_key                 = "REDACTED"
default_tags = {
  owner        = "platform"
  cost_center  = "mindwell-core"
  project      = "mindwell"
}
vnet_address_space             = ["10.20.0.0/16"]
subnet_aks_system              = "10.20.0.0/24"
subnet_aks_workload            = "10.20.1.0/24"
subnet_postgres                = "10.20.2.0/24"
oncall_email                   = "alerts@mindwell.health"
oncall_country_code            = "86"
oncall_phone                   = "13800000000"
aks_version                    = "1.29.4"
aks_service_cidr               = "10.21.0.0/16"
aks_dns_service_ip             = "10.21.0.10"
aks_docker_bridge_cidr         = "172.17.0.1/16"
aks_admin_group_object_ids     = ["00000000-0000-0000-0000-000000000000"]
postgres_sku_name              = "GP_Standard_D4s_v3"
key_vault_admin_object_id      = "00000000-0000-0000-0000-000000000000"
key_vault_allowed_ips          = ["123.123.123.123/32"]
placeholder_openai_api_key     = "sk-REPLACE-ME"
```

### Notes
- Enable an Azure Storage Account backend for Terraform state before multi-user usage.
- Configure Azure Key Vault firewall rules to include GitHub Action runner egress IPs when running in CI.
- Replace the placeholder OpenAI secret with a secure value or remove after CI secret sync is in place.

