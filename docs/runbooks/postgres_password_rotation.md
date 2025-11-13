# Postgres Admin Password Rotation

This runbook covers how to synchronize a new Azure PostgreSQL Flexible Server admin password (`mindwelladmin`) across every secret store and MindWell app. Execute the steps sequentially for each environment (`dev`, `staging`, `prod`).

## Prerequisites

- Generate the new password (for example via `openssl rand -base64 24`) and store it in 1Password under `MindWell <env> Postgres Admin` **before** rotating anywhere else.
- Verify you have permissions for `az postgres flexible-server update`, `az keyvault secret set`, `aws secretsmanager put-secret-value`, updating GitHub Actions secrets, and managing the `mindwell-<env>-api` Azure App Service.
- Export the following environment variables:

```bash
export ENVIRONMENT=dev
export PASSWORD="paste-new-password-here"
export RESOURCE_GROUP="rg-mindwell-${ENVIRONMENT}"
export POSTGRES_SERVER="pgflex-mindwell-${ENVIRONMENT}"
export KEY_VAULT="kv-mindwell-${ENVIRONMENT}"
export BACKEND_APP="mindwell-${ENVIRONMENT}-api"
```

## 1. Update the server password

```bash
az postgres flexible-server update \
  --name "$POSTGRES_SERVER" \
  --resource-group "$RESOURCE_GROUP" \
  --admin-password "$PASSWORD"
```

Wait for status `Succeeded` (`az postgres flexible-server show --name ... --query state`).

## 2. Sync Key Vault

```bash
az keyvault secret set \
  --vault-name "$KEY_VAULT" \
  --name postgres-admin-password \
  --value "$PASSWORD"

az keyvault secret set \
  --vault-name "$KEY_VAULT" \
  --name database-url \
  --value "postgresql+asyncpg://mindwelladmin:${PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com:5432/mindwell_app?sslmode=require"
```

## 3. Update the App Service

```bash
az webapp config appsettings set \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings DATABASE_URL="postgresql+asyncpg://mindwelladmin:${PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com:5432/mindwell_app?sslmode=require"
```

Restart the app (`az webapp restart`). Check `/api/healthz` and the Alembic logs.

## 4. Update GitHub Secrets

- Refresh `DEV_DATABASE_URL`, `DEV_POSTGRES_ADMIN_PASSWORD` (and the equivalents for other environments) via **Settings → Secrets and variables → Actions**.
- For self-hosted runners update `~/.config/mindwell/dev.env` (the `DATABASE_URL` section).

## 5. AWS Secrets Manager (if used)

```bash
aws secretsmanager put-secret-value \
  --secret-id mindwell/${ENVIRONMENT}/postgres/admin-password \
  --secret-string "$PASSWORD"
```

## 6. Validation

1. `source services/backend/.venv/bin/activate && cd services/backend && ALEMBIC_CONFIG=alembic.ini DATABASE_URL="postgresql+asyncpg://mindwelladmin:${PASSWORD}@..." alembic upgrade head`
2. `curl https://mindwell-${ENVIRONMENT}-api.azurewebsites.net/api/healthz`
3. `az webapp log tail --name "$BACKEND_APP"` — verify Alembic applies cleanly with no `invalid password` errors.

## 7. Audit and documentation

- Update the security changelog with the date/ticket/operator.
- Let the on-call channel know the rotation is complete.
- Attach the new secret version link (`Secret Id` from Key Vault) to the tracking ticket.
