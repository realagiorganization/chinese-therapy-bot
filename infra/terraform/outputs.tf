output "resource_group_name" {
  description = "Azure resource group hosting core infrastructure."
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "Azure Kubernetes Service cluster name."
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_api_server_url" {
  description = "AKS Kubernetes API server endpoint."
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
}

output "aks_managed_identity_principal_id" {
  description = "Principal ID of the AKS cluster managed identity (used for workload identity integrations)."
  value       = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

output "aks_kubelet_identity_object_id" {
  description = "Object ID of the AKS kubelet identity (nodes) granted access to Key Vault secrets."
  value       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

output "postgres_server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL flexible server."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "key_vault_uri" {
  description = "Primary Key Vault URI for fetching secrets."
  value       = azurerm_key_vault.main.vault_uri
}

output "application_insights_connection_string" {
  description = "Connection string for the Application Insights instance."
  value       = azurerm_application_insights.platform.connection_string
}

output "application_insights_app_id" {
  description = "Application Insights App ID used for API integrations."
  value       = azurerm_application_insights.platform.app_id
}

output "observability_dashboard_id" {
  description = "Resource ID for the MindWell observability Azure Portal dashboard."
  value       = azurerm_portal_dashboard.platform_overview.id
}

output "s3_bucket_conversation_logs" {
  description = "S3 bucket ARN for conversation logs."
  value       = aws_s3_bucket.conversation_logs.arn
}

output "s3_bucket_summaries" {
  description = "S3 bucket ARN for conversation summaries."
  value       = aws_s3_bucket.summaries.arn
}

output "s3_bucket_media" {
  description = "S3 bucket ARN for therapist media assets."
  value       = aws_s3_bucket.media.arn
}

output "aws_rds_endpoint" {
  description = "Endpoint address for the AWS RDS PostgreSQL instance."
  value       = aws_db_instance.mindwell.address
}

output "aws_rds_credentials_secret_arn" {
  description = "Secrets Manager ARN storing AWS RDS master credentials."
  value       = aws_secretsmanager_secret.rds_master_credentials.arn
}

output "automation_agent_public_ip" {
  description = "Public IP address of the automation agent EC2 instance."
  value       = aws_instance.automation_agent.public_ip
}

output "automation_agent_instance_id" {
  description = "Instance ID of the automation agent EC2 instance."
  value       = aws_instance.automation_agent.id
}

output "ci_runner_role_arn" {
  description = "IAM role ARN for CI Runner Agent workloads."
  value       = aws_iam_role.ci_runner.arn
}

output "cost_budget_resource_id" {
  description = "Resource ID for the monthly Azure cost budget (null when disabled)."
  value       = length(azurerm_consumption_budget_subscription.monthly) > 0 ? azurerm_consumption_budget_subscription.monthly[0].id : null
}
