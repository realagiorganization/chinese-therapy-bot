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

variable "postgres_connection_secret_name" {
  description = "Azure Key Vault secret name storing the database connection string."
  type        = string
  default     = null
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

variable "aws_vpc_cidr" {
  description = "CIDR block for the AWS VPC hosting MindWell auxiliary services."
  type        = string
  default     = "10.60.0.0/16"
}

variable "aws_private_subnet_cidrs" {
  description = "CIDR blocks for private subnets used by AWS RDS and internal workloads."
  type        = list(string)
  default     = ["10.60.1.0/24", "10.60.2.0/24"]
}

variable "aws_public_subnet_cidr" {
  description = "CIDR block for the public subnet hosting automation agents."
  type        = string
  default     = "10.60.10.0/24"
}

variable "aws_az_private_a" {
  description = "AWS availability zone for the first private subnet (defaults to <region>a)."
  type        = string
  default     = null
}

variable "aws_az_private_b" {
  description = "AWS availability zone for the second private subnet (defaults to <region>c)."
  type        = string
  default     = null
}

variable "aws_az_public" {
  description = "AWS availability zone for the public subnet (defaults to <region>a)."
  type        = string
  default     = null
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

variable "aws_rds_instance_class" {
  description = "Instance class for the AWS RDS PostgreSQL instance."
  type        = string
  default     = "db.t4g.medium"
}

variable "aws_rds_engine_version" {
  description = "PostgreSQL engine version for the AWS RDS instance."
  type        = string
  default     = "15.4"
}

variable "aws_rds_database_name" {
  description = "Default database name created on the AWS RDS instance."
  type        = string
  default     = "mindwell"
}

variable "aws_rds_master_username" {
  description = "Master username for the AWS RDS PostgreSQL instance."
  type        = string
  default     = "mindwellapp"
}

variable "aws_rds_allocated_storage" {
  description = "Initial storage (GB) allocated for the AWS RDS instance."
  type        = number
  default     = 100
}

variable "aws_rds_max_allocated_storage" {
  description = "Maximum storage (GB) that the AWS RDS instance can auto-scale to."
  type        = number
  default     = 200
}

variable "aws_rds_multi_az" {
  description = "Whether to enable Multi-AZ replication for the AWS RDS instance."
  type        = bool
  default     = false
}

variable "aws_rds_backup_retention_days" {
  description = "Number of days to retain automated RDS backups."
  type        = number
  default     = 7
}

variable "aws_rds_skip_final_snapshot" {
  description = "Skip creating a final snapshot when destroying the RDS instance (useful for non-prod)."
  type        = bool
  default     = true
}

variable "aws_rds_backup_window" {
  description = "Preferred backup window for the RDS instance (UTC)."
  type        = string
  default     = "03:00-05:00"
}

variable "aws_rds_maintenance_window" {
  description = "Preferred maintenance window for the RDS instance (UTC)."
  type        = string
  default     = "Mon:06:00-Mon:08:00"
}

variable "aws_rds_performance_insights" {
  description = "Enable AWS Performance Insights for the RDS instance."
  type        = bool
  default     = true
}

variable "aws_rds_deletion_protection" {
  description = "Enable deletion protection for the RDS instance."
  type        = bool
  default     = false
}

variable "aws_agent_instance_type" {
  description = "EC2 instance type for automation agents."
  type        = string
  default     = "t3.medium"
}

variable "aws_agent_root_volume_size" {
  description = "Root EBS volume size (GB) for the automation agent instance."
  type        = number
  default     = 40
}

variable "aws_agent_ssh_key_name" {
  description = "Optional SSH key pair name attached to the automation agent instance."
  type        = string
  default     = null
}

variable "aws_agent_enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring for automation agents."
  type        = bool
  default     = false
}

variable "aws_agent_allowed_ssh_cidrs" {
  description = "CIDR blocks permitted to SSH into automation agents."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "aws_agent_user_data" {
  description = "Optional user data script for configuring automation agents."
  type        = string
  default     = null
}

variable "aws_agent_ami_id" {
  description = "Override AMI ID for automation agents (defaults to latest Amazon Linux 2023)."
  type        = string
  default     = null
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
