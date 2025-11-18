mock_provider "azurerm" {
  mock_resource "azurerm_kubernetes_cluster" {
    defaults = {
      kubelet_identity = [{
        object_id                 = "44444444-4444-4444-4444-444444444444"
        client_id                 = "55555555-5555-5555-5555-555555555555"
        user_assigned_identity_id = null
      }]
    }
  }
}

mock_provider "aws" {}

mock_provider "random" {}

run "aks_workload_identity" {
  command = plan

  variables {
    project_name               = "MindWell"
    environment                = "dev"
    azure_subscription_id      = "00000000-0000-0000-0000-000000000000"
    azure_tenant_id            = "11111111-1111-1111-1111-111111111111"
    azure_location             = "eastasia"
    aws_region                 = "ap-northeast-1"
    vnet_address_space         = ["10.30.0.0/16"]
    subnet_aks_system          = "10.30.1.0/24"
    subnet_aks_workload        = "10.30.2.0/24"
    subnet_postgres            = "10.30.3.0/24"
    oncall_email               = "oncall@mindwell.dev"
    oncall_country_code        = "86"
    oncall_phone               = "13800138000"
    aks_version                = "1.29.4"
    aks_service_cidr           = "10.31.0.0/16"
    aks_dns_service_ip         = "10.31.0.10"
    postgres_sku_name          = "GP_Standard_D4s_v3"
    key_vault_admin_object_id  = "33333333-3333-3333-3333-333333333333"
    key_vault_allowed_ips      = ["20.20.20.20"]
    placeholder_openai_api_key = "sk-test-placeholder"
    kubelet_identity_object_id_override = "44444444-4444-4444-4444-444444444444"
  }

  override_data {
    target = data.aws_iam_policy_document.ci_runner_assume
    values = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  assert {
    condition     = azurerm_kubernetes_cluster.core.oidc_issuer_enabled
    error_message = "AKS must expose an OIDC issuer for workload identity."
  }

  assert {
    condition     = azurerm_kubernetes_cluster.core.workload_identity_enabled
    error_message = "AKS workload identity must remain enabled."
  }

  assert {
    condition     = azurerm_kubernetes_cluster.core.network_profile[0].service_cidr == "10.31.0.0/16"
    error_message = "AKS service CIDR should match the dev network plan."
  }

  assert {
    condition     = azurerm_kubernetes_cluster_node_pool.workload.enable_auto_scaling
    error_message = "Workload node pool must keep cluster autoscaler enabled."
  }

  assert {
    condition     = azurerm_kubernetes_cluster_node_pool.workload.max_count == 5
    error_message = "Workload node pool max_count should remain at 5 nodes."
  }

  assert {
    condition     = contains(azurerm_key_vault_access_policy.aks.secret_permissions, "Get")
    error_message = "AKS managed identity must retain Key Vault secret GET permission."
  }

  assert {
    condition     = azurerm_key_vault_access_policy.aks.object_id == "44444444-4444-4444-4444-444444444444"
    error_message = "Tests rely on kubelet identity override wiring; drift indicates the override logic changed."
  }

  assert {
    condition     = azurerm_key_vault.core.network_acls[0].default_action == "Deny"
    error_message = "Key Vault should default to deny traffic outside the allowlist."
  }
}
