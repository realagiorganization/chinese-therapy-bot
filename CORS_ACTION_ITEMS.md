Пункты, которые нужно выполнить, чтобы устранить текущие CORS-проблемы:

1. Проверить фронтенд: в DevTools → Network убедиться, что `/oauth2/start` инициируется исключительно через `window.location` (никаких `fetch`/`axios`). При необходимости переписать обработчик кнопки.
2. Вынести конфигурацию oauth2-proxy в отдельный образ: создать `oauth2-proxy.cfg` со всеми нужными параметрами (`skip_auth_preflight=true`, списки CORS/redirect) и запускать контейнер с `--config=/etc/oauth2-proxy.cfg`.
3. После деплоя проверить whitelists и preflight: обновить `OAUTH2_PROXY_WHITELIST_DOMAINS`/`ALLOWED_REDIRECT_URLS`, затем выполнить `curl -I` на `/oauth2/start` и `curl -X OPTIONS` на `/api/auth/session` с нужным `Origin` — ответы должны быть без редиректов и с `Access-Control-Allow-*`.
4. Рассмотреть альтернативу без CORS: разместить SPA и oauth2-proxy под одним кастомным доменом (Front Door/Traffic Manager), чтобы браузер вообще не выполнял CORS preflight.

Прогресс 12.11:
- `OAUTH2_PROXY_CORS_ALLOWED_ORIGINS` ограничен `https://gray-meadow-0e3af0500.3.azurestaticapps.net`, приложение перезапущено, `OPTIONS https://mindwell-dev-oauth.azurewebsites.net/api/translation/batch` отдаёт `HTTP 200` с `Access-Control-Allow-Origin`.
