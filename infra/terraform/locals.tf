locals {
  default_resource_group_name = "rg-mindwell-${var.environment}"
  default_aks_name            = "aks-mindwell-${var.environment}"
  default_nodepool_name       = "workload"
  default_key_vault_name      = "kv-mindwell-${var.environment}"

  name_suffix = substr(md5(var.environment), 0, 6)

  default_tags = merge(
    {
      environment = var.environment
      project     = "MindWell"
      managed_by  = "Terraform"
    },
    var.tags,
  )
}
