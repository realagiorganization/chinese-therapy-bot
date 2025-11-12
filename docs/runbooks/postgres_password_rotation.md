# Postgres Admin Password Rotation

Этот ранбук описывает, как синхронизировать новый пароль администратора Azure PostgreSQL Flexible Server (`mindwelladmin`) между всеми сторажами секретов и приложениями MindWell. Выполняйте шаги подряд для каждой среды (`dev`, `staging`, `prod`).

## Предусловия

- Получите новый пароль (например, через `openssl rand -base64 24`) и сохраните его в 1Password в записи `MindWell <env> Postgres Admin` **до** начала работ.
- Убедитесь, что у вас есть права на `az postgres flexible-server update`, `az keyvault secret set`, `aws secretsmanager put-secret-value`, изменение GitHub Actions secrets и Azure App Service `mindwell-<env>-api`.
- Экспортируйте переменные окружения:

```bash
export ENVIRONMENT=dev
export PASSWORD="paste-new-password-here"
export RESOURCE_GROUP="rg-mindwell-${ENVIRONMENT}"
export POSTGRES_SERVER="pgflex-mindwell-${ENVIRONMENT}"
export KEY_VAULT="kv-mindwell-${ENVIRONMENT}"
export BACKEND_APP="mindwell-${ENVIRONMENT}-api"
```

## 1. Обновите пароль сервера

```bash
az postgres flexible-server update \
  --name "$POSTGRES_SERVER" \
  --resource-group "$RESOURCE_GROUP" \
  --admin-password "$PASSWORD"
```

Дождитесь статуса `Succeeded` (`az postgres flexible-server show --name ... --query state`).

## 2. Синхронизируйте Key Vault

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

## 3. Обновите App Service

```bash
az webapp config appsettings set \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings DATABASE_URL="postgresql+asyncpg://mindwelladmin:${PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com:5432/mindwell_app?sslmode=require"
```

Перезапустите приложение (`az webapp restart`). Проверьте `/api/healthz` и Alembic логи.

## 4. Обновите GitHub Secrets

- `DEV_DATABASE_URL`, `DEV_POSTGRES_ADMIN_PASSWORD` (и аналоги для других сред) через **Settings → Secrets and variables → Actions**.
- Для self-hosted агентов обновите `~/.config/mindwell/dev.env` (секция `DATABASE_URL`).

## 5. AWS Secrets Manager (если используется)

```bash
aws secretsmanager put-secret-value \
  --secret-id mindwell/${ENVIRONMENT}/postgres/admin-password \
  --secret-string "$PASSWORD"
```

## 6. Валидация

1. `source services/backend/.venv/bin/activate && cd services/backend && ALEMBIC_CONFIG=alembic.ini DATABASE_URL="postgresql+asyncpg://mindwelladmin:${PASSWORD}@..." alembic upgrade head`
2. `curl https://mindwell-${ENVIRONMENT}-api.azurewebsites.net/api/healthz`
3. `az webapp log tail --name "$BACKEND_APP"` — убедитесь, что Alembic применился без ошибок `invalid password`.

## 7. Аудит и документация

- Обновите security changelog с датой/тикетом/оператором.
- Сообщите on-call каналу, что пароль ротации завершён.
- Закрепите ссылку на новую версию секрета (`Secret Id` из Key Vault) в тикете.
