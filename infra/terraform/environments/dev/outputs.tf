output "resource_group_name" {
  description = "Core resource group name."
  value       = azurerm_resource_group.core.name
}

output "aks_cluster_name" {
  description = "AKS cluster name."
  value       = azurerm_kubernetes_cluster.core.name
}

output "aks_cluster_id" {
  description = "AKS cluster resource ID."
  value       = azurerm_kubernetes_cluster.core.id
}

output "aks_oidc_issuer_url" {
  description = "OIDC issuer URL for workload identity."
  value       = azurerm_kubernetes_cluster.core.oidc_issuer_url
}

output "postgres_fqdn" {
  description = "Private FQDN for Azure Postgres flexible server."
  value       = azurerm_postgresql_flexible_server.core.fqdn
}

output "key_vault_uri" {
  description = "Azure Key Vault URI."
  value       = azurerm_key_vault.core.vault_uri
}

output "s3_conversation_logs_bucket" {
  description = "S3 bucket for conversation logs."
  value       = aws_s3_bucket.conversation_logs.bucket
}

output "s3_summaries_bucket" {
  description = "S3 bucket for daily/weekly summaries."
  value       = aws_s3_bucket.summaries.bucket
}

output "s3_media_bucket" {
  description = "S3 bucket for media assets."
  value       = aws_s3_bucket.media_assets.bucket
}

output "ci_runner_role_arn" {
  description = "IAM role ARN for CI runner access to buckets."
  value       = aws_iam_role.ci_runner.arn
}
