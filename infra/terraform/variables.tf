variable "environment" {
  description = "Deployment environment identifier (e.g., dev, staging, prod)."
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription identifier for resource deployment."
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure Active Directory tenant identifier."
  type        = string
}

variable "azure_location" {
  description = "Azure region for resource deployment."
  type        = string
  default     = "eastasia"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group for primary resources."
  type        = string
  default     = null
}

variable "aks_name" {
  description = "Name of the Azure Kubernetes Service cluster."
  type        = string
  default     = null
}

variable "aks_kubernetes_version" {
  description = "Desired Kubernetes version for AKS."
  type        = string
  default     = null
}

variable "aks_system_node_count" {
  description = "Node count for the AKS system node pool."
  type        = number
  default     = 2
}

variable "aks_system_node_vm_size" {
  description = "VM SKU for the AKS system node pool."
  type        = string
  default     = "Standard_D4ds_v5"
}

variable "aks_workload_node_count" {
  description = "Initial node count for the AKS workload node pool."
  type        = number
  default     = 3
}

variable "aks_workload_node_vm_size" {
  description = "VM SKU for the AKS workload node pool."
  type        = string
  default     = "Standard_D8ds_v5"
}

variable "aks_workload_nodepool_name" {
  description = "Name for the workload node pool."
  type        = string
  default     = null
}

variable "vnet_address_space" {
  description = "CIDR block for the MindWell virtual network."
  type        = string
  default     = "10.20.0.0/16"
}

variable "subnet_system_prefix" {
  description = "CIDR prefix for system node pool subnet."
  type        = string
  default     = "10.20.1.0/24"
}

variable "subnet_workload_prefix" {
  description = "CIDR prefix for workload node pool subnet."
  type        = string
  default     = "10.20.2.0/24"
}

variable "subnet_postgres_prefix" {
  description = "CIDR prefix for the delegated PostgreSQL subnet."
  type        = string
  default     = "10.20.3.0/24"
}

variable "postgres_sku_name" {
  description = "SKU for Azure Database for PostgreSQL Flexible Server."
  type        = string
  default     = "GP_Standard_D4ds_v5"
}

variable "postgres_storage_mb" {
  description = "Allocated storage (MB) for PostgreSQL Flexible Server."
  type        = number
  default     = 131072
}

variable "postgres_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "15"
}

variable "postgres_admin_username" {
  description = "Admin username for PostgreSQL Flexible Server."
  type        = string
  default     = "mindwelladmin"
}

variable "postgres_admin_password_secret_name" {
  description = "Azure Key Vault secret name holding the Postgres admin password."
  type        = string
  default     = "postgres-admin-password"
}

variable "aws_account_id" {
  description = "AWS account identifier for IAM role trust relationships."
  type        = string
}

variable "aws_region" {
  description = "AWS region for S3 buckets and Secrets Manager."
  type        = string
  default     = "ap-northeast-1"
}

variable "s3_logs_bucket_name" {
  description = "S3 bucket name for conversation logs."
  type        = string
}

variable "s3_summaries_bucket_name" {
  description = "S3 bucket name for daily/weekly summaries."
  type        = string
}

variable "s3_media_bucket_name" {
  description = "S3 bucket name for therapist media assets."
  type        = string
}

variable "application_insights_name" {
  description = "Name of the Azure Application Insights instance."
  type        = string
  default     = null
}

variable "monthly_cost_budget_amount" {
  description = "Monthly Azure cost budget amount in USD (set to 0 to disable)."
  type        = number
  default     = 0
}

variable "cost_budget_start_date" {
  description = "ISO8601 start date for the Azure cost budget (YYYY-MM-DD)."
  type        = string
  default     = "2025-01-01"
}

variable "cost_budget_end_date" {
  description = "Optional ISO8601 end date for the Azure cost budget (YYYY-MM-DD)."
  type        = string
  default     = "2025-12-31"
}

variable "cost_budget_contact_emails" {
  description = "Email recipients for cost budget threshold notifications."
  type        = list(string)
  default     = []
}

variable "ci_runner_role_name" {
  description = "IAM role name for the CI Runner Agent."
  type        = string
  default     = "mindwell-ci-runner"
}

variable "key_vault_name" {
  description = "Azure Key Vault name."
  type        = string
  default     = null
}

variable "key_vault_admin_object_ids" {
  description = "List of Azure AD object IDs with administrative access to Key Vault."
  type        = list(string)
  default     = []
}

variable "oidc_github_workload_client_id" {
  description = "Client ID for GitHub Actions OIDC workload identity."
  type        = string
  default     = null
}

variable "oidc_issuer" {
  description = "OIDC issuer URI for federated identities (e.g., GitHub)."
  type        = string
  default     = "https://token.actions.githubusercontent.com"
}

variable "tags" {
  description = "Common tags to apply to all resources."
  type        = map(string)
  default     = {}
}
