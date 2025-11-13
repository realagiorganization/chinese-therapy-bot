# Local oauth2-proxy

This docker-compose manifest builds the same custom image (oauth2-proxy + Caddy) used in Azure (`infra/docker/oauth2-proxy/`). Local tests therefore mirror the production settings (`skip_auth_preflight=true`, proxy bound to `127.0.0.1:4181`, etc.).

## Steps

1. Prepare an environment file outside the repository:
   ```bash
   cd infra/local/oauth2-proxy
   mkdir -p ~/.config/mindwell
   cp .env.oauth2-proxy.example ~/.config/mindwell/oauth2-proxy.env
   ```
   The file `~/.config/mindwell/oauth2-proxy.env` stays out of git and lives only on your machine.
2. Populate `~/.config/mindwell/oauth2-proxy.env` with your OIDC configuration:
   - `OAUTH2_PROXY_CLIENT_ID` / `OAUTH2_PROXY_CLIENT_SECRET` — application credentials from your provider (Azure AD, Google Workspace, etc.).
   - `OAUTH2_PROXY_COOKIE_SECRET` — 32-byte hex string (`openssl rand -hex 32`).
   - `OAUTH2_PROXY_OIDC_ISSUER_URL` and `OAUTH2_PROXY_REDIRECT_URL` must match the provider settings.
   - `OAUTH2_PROXY_UPSTREAMS` defaults to `http://host.docker.internal:8000`, which targets the locally running FastAPI backend.
   - When serving from `http://localhost`, set `OAUTH2_PROXY_COOKIE_SECURE=false`, omit `OAUTH2_PROXY_COOKIE_DOMAIN`, and enable `OAUTH2_PROXY_SKIP_AUTH_PREFLIGHT=true` so CORS preflight (`OPTIONS`) requests bypass auth.
3. Build and start the container:
   ```bash
   docker compose up --build -d
   ```
4. Configure the frontend with `VITE_API_BASE_URL=http://localhost:4180` so `/api/*` requests flow through oauth2-proxy. Clear the `_oauth2_proxy` cookie between tests.

The container exposes `http://localhost:4180`. On Linux ensure Docker supports `host.docker.internal`; otherwise set `OAUTH2_PROXY_UPSTREAMS=http://127.0.0.1:8000` and add `network_mode: "host"` to `docker-compose.yml`.
