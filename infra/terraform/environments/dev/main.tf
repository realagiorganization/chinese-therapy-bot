terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.113"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Configure a remote backend (e.g., Azure Storage) before running `terraform init` in CI.
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

locals {
  name_prefix    = lower(replace(var.project_name, " ", "-"))
  location       = var.azure_location
  environment    = var.environment
  tags           = merge(var.default_tags, { environment = var.environment })
  aks_name       = "${lower(replace(var.project_name, " ", ""))}-${var.environment}-aks"
  log_workspace  = "${var.project_name} ${var.environment} Logs"
  postgres_name  = "${lower(replace(var.project_name, " ", ""))}-${var.environment}-pg"
  key_vault_name = substr(replace("${var.project_name}${var.environment}kv", "-", ""), 0, 24)
}

# ---------------------------
# Azure Resource Group & Networking
# ---------------------------

resource "azurerm_resource_group" "core" {
  name     = "${local.name_prefix}-${var.environment}-rg"
  location = local.location
  tags     = local.tags
}

resource "azurerm_virtual_network" "core" {
  name                = "${local.name_prefix}-${var.environment}-vnet"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  address_space       = var.vnet_address_space
  tags                = local.tags
}

resource "azurerm_subnet" "aks_system" {
  name                 = "aks-system"
  resource_group_name  = azurerm_resource_group.core.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [var.subnet_aks_system]
}

resource "azurerm_subnet" "aks_workload" {
  name                 = "aks-workload"
  resource_group_name  = azurerm_resource_group.core.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [var.subnet_aks_workload]
}

resource "azurerm_subnet" "postgres" {
  name                 = "postgres"
  resource_group_name  = azurerm_resource_group.core.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [var.subnet_postgres]

  delegation {
    name = "postgres-flexible-server"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.postgres_name}.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${local.postgres_name}-dns-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tags
}

# ---------------------------
# Azure Observability
# ---------------------------

resource "azurerm_log_analytics_workspace" "core" {
  name                = "${local.name_prefix}-${var.environment}-law"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.tags
}

resource "azurerm_monitor_action_group" "oncall" {
  name                = "${local.name_prefix}-${var.environment}-oncall"
  resource_group_name = azurerm_resource_group.core.name
  short_name          = "${substr(local.name_prefix, 0, 6)}on"

  email_receiver {
    name          = "primary-oncall"
    email_address = var.oncall_email
  }

  sms_receiver {
    name        = "oncall-sms"
    country_code = var.oncall_country_code
    phone_number = var.oncall_phone
  }

  tags = local.tags
}

resource "azurerm_dashboard" "observability" {
  name                = "${local.name_prefix}-${var.environment}-observability"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  tags                = local.tags

  dashboard_properties = templatefile("${path.module}/templates/azure_dashboard.json.tftpl", {
    workspace_id     = azurerm_log_analytics_workspace.core.id
    workspace_guid   = azurerm_log_analytics_workspace.core.workspace_id
    aks_resource_id  = azurerm_kubernetes_cluster.core.id
    environment      = var.environment
  })
}

resource "azurerm_monitor_metric_alert" "aks_node_cpu" {
  name                = "${local.name_prefix}-${var.environment}-aks-node-cpu"
  resource_group_name = azurerm_resource_group.core.name
  scopes              = [azurerm_kubernetes_cluster.core.id]
  description         = "Alert when AKS node pool average CPU exceeds threshold"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.aks_cpu_alert_threshold
  }

  action {
    action_group_id = azurerm_monitor_action_group.oncall.id
  }

  tags = local.tags
}

# ---------------------------
# Azure Kubernetes Service
# ---------------------------

resource "azurerm_kubernetes_cluster" "core" {
  name                = local.aks_name
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  dns_prefix          = "${local.name_prefix}-${var.environment}-aks"
  kubernetes_version  = var.aks_version

  default_node_pool {
    name                = "system"
    vm_size             = var.aks_system_vm_size
    node_count          = var.aks_system_node_count
    os_disk_size_gb     = 64
    vnet_subnet_id      = azurerm_subnet.aks_system.id
    orchestrator_version = var.aks_version
    type                = "VirtualMachineScaleSets"
    upgrade_settings {
      max_surge = var.aks_node_max_surge
    }
    mode = "System"
  }

  identity {
    type = "SystemAssigned"
  }

  api_server_access_profile {
    authorized_ip_ranges = var.api_server_allowed_ips
  }

  network_profile {
    network_plugin     = "azure"
    load_balancer_sku  = "standard"
    service_cidr       = var.aks_service_cidr
    dns_service_ip     = var.aks_dns_service_ip
    docker_bridge_cidr = var.aks_docker_bridge_cidr
  }

  azure_active_directory_role_based_access_control {
    managed               = true
    admin_group_object_ids = var.aks_admin_group_object_ids
    azure_rbac_enabled    = true
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  sku_tier = "Paid"

  tags = local.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  name                  = "workload"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.core.id
  vm_size               = var.aks_workload_vm_size
  node_count            = var.aks_workload_node_count
  max_count             = var.aks_workload_max_count
  min_count             = var.aks_workload_min_count
  enable_auto_scaling   = true
  orchestrator_version  = var.aks_version
  vnet_subnet_id        = azurerm_subnet.aks_workload.id
  mode                  = "User"
  tags                  = local.tags
}

resource "azurerm_monitor_diagnostic_setting" "aks_logs" {
  name               = "${local.name_prefix}-${var.environment}-aks-diag"
  target_resource_id = azurerm_kubernetes_cluster.core.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.core.id

  enabled_log {
    category = "kube-apiserver"
  }

  enabled_log {
    category = "cluster-autoscaler"
  }

  metric {
    category = "AllMetrics"
  }
}

# ---------------------------
# Azure PostgreSQL Flexible Server
# ---------------------------

resource "random_password" "postgres_admin" {
  length  = 20
  special = true
}

resource "azurerm_postgresql_flexible_server" "core" {
  name                   = local.postgres_name
  location               = azurerm_resource_group.core.location
  resource_group_name    = azurerm_resource_group.core.name
  version                = var.postgres_version
  delegated_subnet_id    = azurerm_subnet.postgres.id
  sku_name               = var.postgres_sku_name
  storage_mb             = var.postgres_storage_mb
  backup_retention_days  = var.postgres_backup_retention_days
  geo_redundant_backup_enabled = var.postgres_geo_redundant_backup_enabled
  administrator_login    = var.postgres_admin_username
  administrator_password = random_password.postgres_admin.result

  high_availability {
    mode = var.postgres_ha_mode
  }

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = true
  }

  maintenance_window {
    day_of_week  = var.postgres_maintenance_day
    start_hour   = var.postgres_maintenance_hour
    start_minute = 0
  }

  private_dns_zone_id = azurerm_private_dns_zone.postgres.id

  tags = local.tags
}

resource "azurerm_postgresql_flexible_server_database" "mindwell" {
  name      = "mindwell"
  server_id = azurerm_postgresql_flexible_server.core.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ---------------------------
# Azure Key Vault
# ---------------------------

resource "azurerm_key_vault" "core" {
  name                = local.key_vault_name
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  tenant_id           = var.azure_tenant_id
  sku_name            = "standard"
  soft_delete_retention_days = 14
  purge_protection_enabled   = true

  access_policy {
    tenant_id = var.azure_tenant_id
    object_id = var.key_vault_admin_object_id

    secret_permissions = ["Get", "List", "Set", "Delete", "Recover", "Backup", "Restore"]
  }

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.key_vault_allowed_ips
  }

  tags = local.tags
}

resource "azurerm_key_vault_access_policy" "aks" {
  key_vault_id = azurerm_key_vault.core.id
  tenant_id    = var.azure_tenant_id
  object_id    = azurerm_kubernetes_cluster.core.kubelet_identity[0].object_id

  secret_permissions = ["Get"]
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = "postgres-admin-password"
  value        = random_password.postgres_admin.result
  key_vault_id = azurerm_key_vault.core.id
}

# ---------------------------
# AWS Buckets & IAM
# ---------------------------

data "aws_iam_policy_document" "ci_runner_assume" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    sid    = "AllowBucketAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.conversation_logs.arn,
      "${aws_s3_bucket.conversation_logs.arn}/*",
      aws_s3_bucket.summaries.arn,
      "${aws_s3_bucket.summaries.arn}/*",
      aws_s3_bucket.media_assets.arn,
      "${aws_s3_bucket.media_assets.arn}/*"
    ]
  }
}

resource "aws_iam_role" "ci_runner" {
  name               = "${local.name_prefix}-${var.environment}-ci-runner"
  assume_role_policy = data.aws_iam_policy_document.ci_runner_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "ci_runner_s3" {
  name   = "${local.name_prefix}-${var.environment}-ci-s3"
  role   = aws_iam_role.ci_runner.id
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_s3_bucket" "conversation_logs" {
  bucket = "${local.name_prefix}-${var.environment}-conversation-logs"
  force_destroy = false

  tags = merge(local.tags, {
    data_classification = "sensitive"
  })
}

resource "aws_s3_bucket" "summaries" {
  bucket = "${local.name_prefix}-${var.environment}-summaries"
  force_destroy = false

  tags = merge(local.tags, {
    data_classification = "confidential"
  })
}

resource "aws_s3_bucket" "media_assets" {
  bucket = "${local.name_prefix}-${var.environment}-media"
  force_destroy = false

  tags = merge(local.tags, {
    data_classification = "public"
  })
}

resource "aws_s3_bucket_versioning" "conversation_logs" {
  bucket = aws_s3_bucket.conversation_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "summaries" {
  bucket = aws_s3_bucket.summaries.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "media_assets" {
  bucket = aws_s3_bucket.media_assets.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "conversation_logs" {
  bucket = aws_s3_bucket.conversation_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "summaries" {
  bucket = aws_s3_bucket.summaries.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media_assets" {
  bucket = aws_s3_bucket.media_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "conversation_logs" {
  bucket                  = aws_s3_bucket.conversation_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "summaries" {
  bucket                  = aws_s3_bucket.summaries.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "media_assets" {
  bucket                  = aws_s3_bucket.media_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = false
  restrict_public_buckets = true
}

# ---------------------------
# AWS Secrets Manager
# ---------------------------

resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "${local.name_prefix}/${var.environment}/openai-api-key"
  description = "Azure OpenAI key replica for cross-cloud orchestration"
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.placeholder_openai_api_key
}
