resource "azurerm_key_vault" "main" {
  name                        = coalesce(var.key_vault_name, local.default_key_vault_name)
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = var.azure_tenant_id
  sku_name                    = "standard"
  soft_delete_enabled         = true
  purge_protection_enabled    = true
  enable_rbac_authorization   = true
  public_network_access_enabled = false
  tags                        = local.default_tags
}

resource "azurerm_role_assignment" "key_vault_admins" {
  for_each = toset(var.key_vault_admin_object_ids)

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = each.value
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = var.postgres_admin_password_secret_name
  value        = random_password.postgres_admin.result
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    description = "Initial PostgreSQL flexible server administrator password."
  }
}
