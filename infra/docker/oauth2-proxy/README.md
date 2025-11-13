# oauth2-proxy + Caddy

Папка содержит минимальный Docker-контекст для MindWell-версии oauth2-proxy:

- Multi-stage образ берёт `quay.io/oauth2-proxy/oauth2-proxy:v7.8.1` и `caddy:2.9-alpine`: Caddy
  публикует `:4180`, а `oauth2-proxy` слушает `127.0.0.1:4181`, что позволяет переопределять
  заголовки без пересборки бинарника.
- `oauth2-proxy.cfg` устанавливает `http_address=127.0.0.1:4181`, `skip_auth_preflight=true`, проброс
  `X-Auth-Request-*` заголовков и прочие общие параметры.
- Секреты (`*_CLIENT_SECRET`, `*_COOKIE_SECRET`, `OAUTH2_PROXY_UPSTREAMS`, allowlists и пр.) по-прежнему
  задаются через переменные окружения (`OAUTH2_PROXY_*`).

## Сборка и публикация

```bash
az acr login --name mindwelloauthacr
docker build -t mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors infra/docker/oauth2-proxy
docker push mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors
```

`deploy_azure_hosting.sh` по умолчанию использует `mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors`,
поэтому дополнительный флаг не нужен. При необходимости передайте `--oauth-image <registry>/<tag>` (или
экспортируйте `OAUTH_IMAGE`). App Service по-прежнему читает `WEBSITES_PORT=4180` и значения из
`~/.config/mindwell/oauth2-proxy.azure.json` (JSON-объект с парами `"OAUTH2_PROXY_*": "<значение>"`).

## Проверка после деплоя

1. В `OAUTH2_PROXY_CORS_ALLOWED_ORIGINS` оставьте только актуальный SPA-домен.
2. Обновите `OAUTH2_PROXY_ALLOWED_REDIRECT_URLS` / `WHITELIST_DOMAINS`.
3. Настройте CORS в App Service:
   ```bash
   az webapp update \
     --name mindwell-dev-oauth \
     --resource-group rg-mindwell-dev \
     --set siteConfig.cors.allowedOrigins='["https://<frontend>"]' \
           siteConfig.cors.supportCredentials=true
   ```
4. Убедитесь, что preflight и основные запросы содержат нужные заголовки:
   ```bash
   curl -i -X OPTIONS \
     -H "Origin: https://<frontend>" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" \
     https://<oauth-host>/api/auth/demo
   curl -i \
     -H "Origin: https://<frontend>" \
     "https://<oauth-host>/oauth2/start?rd=https://<frontend>/api/auth/demo"
   ```
   В ответах должны присутствовать `Access-Control-Allow-Origin` и `Access-Control-Allow-Credentials: true`.
