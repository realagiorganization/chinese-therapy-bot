# oauth2-proxy + Caddy

This directory contains the minimal Docker context for the MindWell variant of oauth2-proxy:

- The multi-stage image pulls `quay.io/oauth2-proxy/oauth2-proxy:v7.8.1` plus `caddy:2.9-alpine`. Caddy
  serves `:4180` while `oauth2-proxy` listens on `127.0.0.1:4181`, which makes it easy to override headers
  without rebuilding the upstream binary.
- `oauth2-proxy.cfg` sets `http_address=127.0.0.1:4181`, `skip_auth_preflight=true`, forwards the
  `X-Auth-Request-*` headers, and applies the shared defaults.
- Secrets (`*_CLIENT_SECRET`, `*_COOKIE_SECRET`, `OAUTH2_PROXY_UPSTREAMS`, allowlists, etc.) are still
  provided via environment variables (`OAUTH2_PROXY_*`).

## Build and publish

```bash
az acr login --name mindwelloauthacr
docker build -t mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors infra/docker/oauth2-proxy
docker push mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors
```

`deploy_azure_hosting.sh` defaults to `mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors`, so no extra flag
is needed. If you host the image elsewhere, pass `--oauth-image <registry>/<tag>` (or export `OAUTH_IMAGE`).
App Service still reads `WEBSITES_PORT=4180` plus the values from
`~/.config/mindwell/oauth2-proxy.azure.json` (a JSON object of `"OAUTH2_PROXY_*": "<value>"` pairs).

## Post-deploy verification

1. Keep only the live SPA domain in `OAUTH2_PROXY_CORS_ALLOWED_ORIGINS`.
2. Refresh `OAUTH2_PROXY_ALLOWED_REDIRECT_URLS` / `WHITELIST_DOMAINS`.
3. Configure App Service CORS:
   ```bash
   az webapp update \
     --name mindwell-dev-oauth \
     --resource-group rg-mindwell-dev \
     --set siteConfig.cors.allowedOrigins='["https://<frontend>"]' \
           siteConfig.cors.supportCredentials=true
   ```
4. Confirm both preflight and main requests have the expected headers:
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
   Responses must include `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials: true`.
