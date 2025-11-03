resource "azurerm_monitor_action_group" "oncall" {
  name                = "ag-mindwell-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "mindwell"
  enabled             = true
  tags                = local.default_tags

  email_receiver {
    name          = "platform-team"
    email_address = "infra-alerts@example.com"
  }
}

resource "azurerm_application_insights" "platform" {
  name                 = coalesce(var.application_insights_name, "appi-mindwell-${var.environment}")
  location             = azurerm_resource_group.main.location
  resource_group_name  = azurerm_resource_group.main.name
  workspace_id         = azurerm_log_analytics_workspace.main.id
  application_type     = "web"
  retention_in_days    = 30
  sampling_percentage  = 100
  daily_data_cap_in_gb = 5
  tags                 = local.default_tags
}

resource "azurerm_monitor_metric_alert" "aks_cpu" {
  name                 = "aks-cpu-${var.environment}"
  resource_group_name  = azurerm_resource_group.main.name
  scopes               = [azurerm_kubernetes_cluster.main.id]
  description          = "Alerts when AKS node pool average CPU exceeds threshold."
  severity             = 3
  frequency            = "PT5M"
  window_size          = "PT5M"
  auto_mitigate        = true
  target_resource_type = "Microsoft.ContainerService/managedClusters"

  criteria {
    metric_namespace = "Insights.Container/containers"
    metric_name      = "cpuUsageNanoCores"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 700000000 # ~70% utilization assuming 1 core = 1e9
  }

  action {
    action_group_id = azurerm_monitor_action_group.oncall.id
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert" "app_errors" {
  name                = "app-error-rate-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  description         = "Alerts when application traces log more than the allowed threshold of errors in a 5-minute window."
  severity            = 3
  enabled             = true
  data_source_id      = azurerm_log_analytics_workspace.main.id
  query_type          = "ResultCount"
  query               = <<-KQL
      AppTraces
      | where SeverityLevel >= 3
      | summarize ErrorCount = count() by bin(TimeGenerated, 5m)
    KQL
  frequency           = 5
  time_window         = 5

  action {
    action_group = [azurerm_monitor_action_group.oncall.id]
  }

  trigger {
    operator  = "GreaterThan"
    threshold = 20
  }
}

locals {
  observability_dashboard_definition = jsonencode({
    "$schema" = "https://github.com/Microsoft/dashboard-examples/raw/master/PortalDashboardSchema/portal-dashboard.json"
    "lenses" = {
      "0" = {
        "order" = 0
        "parts" = {
          "0" = {
            "position" = {
              "x"       = 0
              "y"       = 0
              "rowSpan" = 3
              "colSpan" = 6
            }
            "metadata" = {
              "type" = "Extension/HubsExtension/PartType/MarkdownPart"
              "settings" = {
                "content" = {
                  "settings" = {
                    "content" = format(
                      "## MindWell Platform Overview\n- **Environment:** %s\n- **Region:** %s\n- **AKS Cluster:** %s\n- **Application Insights:** %s",
                      var.environment,
                      var.azure_location,
                      azurerm_kubernetes_cluster.main.name,
                      azurerm_application_insights.platform.name,
                    )
                  }
                }
              }
              "inputs" = []
            }
          }
          "1" = {
            "position" = {
              "x"       = 0
              "y"       = 3
              "rowSpan" = 6
              "colSpan" = 12
            }
            "metadata" = {
              "type" = "Extension/Microsoft_Azure_Monitoring/PartType/MetricChartPart"
              "inputs" = [
                {
                  "name"  = "Scope"
                  "value" = azurerm_application_insights.platform.id
                },
                {
                  "name" = "Metrics"
                  "value" = [
                    {
                      "resourceMetadata" = {
                        "id" = azurerm_application_insights.platform.id
                      }
                      "name"        = "requests/count"
                      "namespace"   = "Microsoft.Insights/components"
                      "aggregation" = "Count"
                    },
                    {
                      "resourceMetadata" = {
                        "id" = azurerm_application_insights.platform.id
                      }
                      "name"        = "requests/failed"
                      "namespace"   = "Microsoft.Insights/components"
                      "aggregation" = "Count"
                    }
                  ]
                }
              ]
              "settings" = {
                "content" = {
                  "settings" = {
                    "title" = "Request Volume vs Failures (Last 24h)"
                  }
                }
              }
            }
          }
        }
      }
    }
    "metadata" = {
      "model" = {
        "timeRange" = {
          "value" = {
            "relative" = "24h"
          }
          "type" = "MsPortalFx_Composition/TimeContext"
        }
      }
    }
  })
}

resource "azurerm_portal_dashboard" "platform_overview" {
  name                 = "dash-mindwell-${var.environment}"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  tags                 = local.default_tags
  dashboard_properties = local.observability_dashboard_definition
}

resource "azurerm_consumption_budget_subscription" "monthly" {
  count           = var.monthly_cost_budget_amount > 0 && length(var.cost_budget_contact_emails) > 0 ? 1 : 0
  name            = "cost-budget-${var.environment}"
  subscription_id = "/subscriptions/${var.azure_subscription_id}"
  amount          = var.monthly_cost_budget_amount
  time_grain      = "Monthly"

  time_period {
    start_date = var.cost_budget_start_date
    end_date   = var.cost_budget_end_date
  }

  notification {
    enabled        = true
    threshold      = 80
    threshold_type = "Actual"
    operator       = "GreaterThan"
    contact_emails = var.cost_budget_contact_emails
  }

  notification {
    enabled        = true
    threshold      = 95
    threshold_type = "Actual"
    operator       = "GreaterThan"
    contact_emails = var.cost_budget_contact_emails
  }
}
