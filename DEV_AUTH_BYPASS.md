# Developer Auth Bypass

## Email oauth2-proxy flow (default)
- Start the backend (`mindwell-api`) alongside oauth2-proxy configured to protect the `/api/*` routes.
- Open the web client (http://localhost:5173) and provide your email in the first form. Submitting the form redirects the browser to `/oauth2/start?rd=<current_page>` with the email in `login_hint`.
- After completing the upstream login, oauth2-proxy forwards identity headers (`X-Auth-Request-Email`, `X-Auth-Request-User`, etc.) to the backend.
- After returning from oauth2-proxy the login panel detects the pending oauth flag set by the email button, calls `POST /api/auth/session`, and stores the resulting JWT/refresh tokens via `AuthContext.setTokens`. The page no longer exchanges oauth sessions implicitly unless the user initiated the email flow.
- Rationale: the backend now trusts oauth2-proxy as the primary identity provider instead of performing its own OTP or Google code exchange.

### Token storage snapshot
- Successful email or demo flows persist tokens through `AuthContext.setTokens`, storing `mindwell:auth` in `localStorage` and mirroring state in `tokenStore`.
- Stored JSON resembles `{"accessToken":"<JWT>","refreshToken":"<opaque>","expiresAt":1700000000000}` with an epoch expiry in milliseconds.
- Clearing the entry or calling `AuthContext.clearTokens` drops authentication state immediately.

## Demo code exchange (allowlisted)
- Administrators maintain an allowlist in the JSON file referenced by `DEMO_CODE_FILE` (sample: `services/backend/config/demo_codes.json`).
- Each entry supports `chat_token_quota` (chat turns before the subscription prompt). If omitted, the backend falls back to `CHAT_TOKEN_DEMO_QUOTA`.
- Enter a permitted code in the second form on the login panel; the frontend submits `POST /api/auth/demo` with that value.
- The backend validates the code against the registry, provisions a dedicated demo `User` for that exact code (or loads the existing one), enforces the demo chat quota, and returns JWT/refresh tokens. Demo users are isolated from email accounts; chat credits are tracked per-code.
- When chat tokens reach zero, the web client renders a subscription overlay and blocks further chat submissions until the quota is replenished.

## Resetting state
- Use the **Sign out** button in the header or clear the `mindwell:auth` key to return to the login screen.
- When experimenting with oauth2-proxy, also clear the proxy cookies (default `_oauth2_proxy`) to force a full reauthentication cycle.

## Local oauth2-proxy harness
- The `infra/local/oauth2-proxy/` directory ships a `docker-compose.yml` plus an example `.env` for spinning up the proxy beside the local backend.
- Copy `.env.oauth2-proxy.example` to `~/.config/mindwell/oauth2-proxy.env`, populate it with your OIDC provider values (remember `OAUTH2_PROXY_COOKIE_SECURE=false` and `OAUTH2_PROXY_SKIP_AUTH_PREFLIGHT=true` for local dev), and run `docker compose up -d` in that directory.
- Set the frontend’s `VITE_API_BASE_URL=http://localhost:4180` so `/api/*` calls go through the proxy and pick up the required `X-Auth-Request-*` headers.
