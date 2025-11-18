resource "azurerm_kubernetes_cluster" "main" {
  name                = coalesce(var.aks_name, local.default_aks_name)
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "mindwell-${var.environment}"

  kubernetes_version = var.aks_kubernetes_version

  default_node_pool {
    name                = "system"
    node_count          = var.aks_system_node_count
    vm_size             = var.aks_system_node_vm_size
    vnet_subnet_id      = azurerm_subnet.system.id
    os_disk_size_gb     = 128
    only_critical_addons_enabled = true
    orchestrator_version        = var.aks_kubernetes_version
  }

  identity {
    type = "SystemAssigned"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    dns_service_ip    = "10.2.0.10"
    service_cidr      = "10.2.0.0/24"
  }

  monitor_metrics {
    annotations = {
      "monitoring.mindwell.cloud/enabled" = "true"
    }
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = local.default_tags
}

resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  name                  = coalesce(var.aks_workload_nodepool_name, local.default_nodepool_name)
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.aks_workload_node_vm_size
  node_count            = var.aks_workload_node_count
  mode                  = "User"
  os_type               = "Linux"
  vnet_subnet_id        = azurerm_subnet.workload.id

  enable_auto_scaling = true
  min_count           = 2
  max_count           = 6

  tags = local.default_tags
}

resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

resource "azurerm_federated_identity_credential" "github_actions" {
  count = var.oidc_github_workload_client_id == null ? 0 : 1

  name                = "github-actions-aks-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = var.oidc_issuer
  subject             = "repo:realagiorganization/chinese-therapy-bot:ref:refs/heads/main"
  parent_id           = azurerm_kubernetes_cluster.main.identity[0].principal_id
}
