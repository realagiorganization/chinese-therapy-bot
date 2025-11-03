resource "random_password" "postgres_admin" {
  length  = 20
  special = true
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "pgflex-mindwell-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = var.postgres_version
  delegated_subnet_id    = azurerm_subnet.postgres.id
  administrator_login    = var.postgres_admin_username
  administrator_password = random_password.postgres_admin.result
  zone                   = "1"

  sku_name   = var.postgres_sku_name
  storage_mb = var.postgres_storage_mb

  backup_retention_days        = 14
  geo_redundant_backup_enabled = true

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = true
  }

  high_availability {
    mode                      = "ZoneRedundant"
    standby_availability_zone = "2"
  }

  depends_on = [
    azurerm_subnet.postgres,
  ]

  tags = local.default_tags
}

resource "azurerm_postgresql_flexible_server_configuration" "timezone" {
  name      = "timezone"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "Asia/Shanghai"
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "mindwell_app"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}
