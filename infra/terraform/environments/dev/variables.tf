variable "project_name" {
  description = "Top-level project name used for resource naming."
  type        = string
}

variable "environment" {
  description = "Short environment name (e.g. dev, staging, prod)."
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription identifier."
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure AD tenant identifier."
  type        = string
}

variable "azure_location" {
  description = "Azure region for core resources (e.g. eastasia)."
  type        = string
}

variable "aws_region" {
  description = "AWS region for S3 buckets (e.g. ap-northeast-1)."
  type        = string
}

variable "default_tags" {
  description = "Common resource tags."
  type        = map(string)
  default     = {}
}

variable "vnet_address_space" {
  description = "VNet CIDR ranges."
  type        = list(string)
}

variable "subnet_aks_system" {
  description = "CIDR for AKS system node pool."
  type        = string
}

variable "subnet_aks_workload" {
  description = "CIDR for AKS workload node pool."
  type        = string
}

variable "subnet_postgres" {
  description = "CIDR for delegated Postgres subnet."
  type        = string
}

variable "log_retention_days" {
  description = "Log Analytics retention period."
  type        = number
  default     = 30
}

variable "oncall_email" {
  description = "Primary on-call notification email."
  type        = string
}

variable "oncall_country_code" {
  description = "Country code for SMS alerts (e.g. 86)."
  type        = string
}

variable "oncall_phone" {
  description = "Phone number for SMS alerts."
  type        = string
}

variable "aks_cpu_alert_threshold" {
  description = "CPU threshold for AKS node alert."
  type        = number
  default     = 80
}

variable "aks_version" {
  description = "AKS Kubernetes version (e.g. 1.29.4)."
  type        = string
}

variable "aks_system_vm_size" {
  description = "VM size for AKS system node pool."
  type        = string
  default     = "Standard_D4s_v3"
}

variable "aks_system_node_count" {
  description = "Node count for AKS system pool."
  type        = number
  default     = 2
}

variable "aks_node_max_surge" {
  description = "Max surge during upgrades."
  type        = string
  default     = "33%"
}

variable "api_server_allowed_ips" {
  description = "CIDR ranges with access to AKS API server."
  type        = list(string)
  default     = []
}

variable "aks_service_cidr" {
  description = "AKS service CIDR."
  type        = string
}

variable "aks_dns_service_ip" {
  description = "AKS DNS service IP."
  type        = string
}

variable "aks_admin_group_object_ids" {
  description = "Azure AD group object IDs with AKS admin access."
  type        = list(string)
  default     = []
}

variable "aks_workload_vm_size" {
  description = "VM size for AKS workload pool."
  type        = string
  default     = "Standard_D8s_v5"
}

variable "aks_workload_node_count" {
  description = "Initial node count for workload pool."
  type        = number
  default     = 2
}

variable "aks_workload_min_count" {
  description = "Minimum nodes for autoscaler."
  type        = number
  default     = 1
}

variable "aks_workload_max_count" {
  description = "Maximum nodes for autoscaler."
  type        = number
  default     = 5
}

variable "postgres_version" {
  description = "Azure Postgres version."
  type        = string
  default     = "14"
}

variable "postgres_sku_name" {
  description = "Azure Postgres SKU (e.g. GP_Standard_D4s_v3)."
  type        = string
}

variable "postgres_storage_mb" {
  description = "Postgres allocated storage in MB."
  type        = number
  default     = 131072
}

variable "postgres_backup_retention_days" {
  description = "Postgres backup retention period."
  type        = number
  default     = 14
}

variable "postgres_geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backups for Postgres."
  type        = bool
  default     = true
}

variable "postgres_admin_username" {
  description = "Postgres administrator username."
  type        = string
  default     = "mindwelladmin"
}

variable "postgres_ha_mode" {
  description = "High availability mode (e.g. ZoneRedundant or SameZone)."
  type        = string
  default     = "ZoneRedundant"
}

variable "postgres_maintenance_day" {
  description = "Maintenance window day of week (0=Sunday)."
  type        = number
  default     = 6
}

variable "postgres_maintenance_hour" {
  description = "Maintenance window hour (0-23 UTC)."
  type        = number
  default     = 22
}

variable "key_vault_admin_object_id" {
  description = "Azure AD object ID for KV admin access."
  type        = string
}

variable "key_vault_allowed_ips" {
  description = "IPv4 ranges allowed to access Key Vault."
  type        = list(string)
  default     = []
}

variable "placeholder_openai_api_key" {
  description = "Temporary placeholder secret for OpenAI key sync."
  type        = string
  sensitive   = true
}

variable "kubelet_identity_object_id_override" {
  description = "Optional override used in tests when the kubelet managed identity is not available."
  type        = string
  default     = ""
}
