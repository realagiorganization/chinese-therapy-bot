# Локальный oauth2-proxy

Этот docker-compose манифест помогает запустить oauth2-proxy рядом с локальным бекендом MindWell, чтобы тестировать email-авторизацию без обращения к демо-кодам.

## Шаги

1. Подготовьте файл окружения вне репозитория:
   ```bash
   cd infra/local/oauth2-proxy
   mkdir -p ~/.config/mindwell
   cp .env.oauth2-proxy.example ~/.config/mindwell/oauth2-proxy.env
   ```
   Файл `~/.config/mindwell/oauth2-proxy.env` не попадает в git и хранится только локально.
2. Заполните `~/.config/mindwell/oauth2-proxy.env` значениями вашей OIDC-конфигурации:
   - `OAUTH2_PROXY_CLIENT_ID` / `OAUTH2_PROXY_CLIENT_SECRET` — параметры приложения в провайдере (Azure AD, Google Workspace и т.д.).
   - `OAUTH2_PROXY_COOKIE_SECRET` — 32-байтная строка в hex (`openssl rand -hex 32`).
   - `OAUTH2_PROXY_OIDC_ISSUER_URL` и `OAUTH2_PROXY_REDIRECT_URL` должны совпадать с настройками приложения.
   - `OAUTH2_PROXY_UPSTREAMS` по умолчанию указывает на `http://host.docker.internal:8000`, что соответствует локально запущенному FastAPI.
   - Для локального `http://localhost` обязательно задайте `OAUTH2_PROXY_COOKIE_SECURE=false`, уберите `OAUTH2_PROXY_COOKIE_DOMAIN` и включите `OAUTH2_PROXY_SKIP_AUTH_PREFLIGHT=true`, чтобы CORS preflight (`OPTIONS`) проходил без авторизации.
3. Запустите контейнер:
   ```bash
   docker compose up -d
   ```
4. Установите для фронтенда `VITE_API_BASE_URL=http://localhost:4180`, чтобы запросы шли через oauth2-proxy. Очистите куки `_oauth2_proxy` при повторных тестах.

Контейнер публикует `http://localhost:4180`. При развороте на Linux убедитесь, что Docker поддерживает `host.docker.internal`. Если нет — замените значение `OAUTH2_PROXY_UPSTREAMS` на `http://127.0.0.1:8000` и добавьте флаг `network_mode: "host"` в `docker-compose.yml`.
