# Developer Auth Bypass

## Email oauth2-proxy flow (default)
- Start the backend (`mindwell-api`) alongside oauth2-proxy configured to protect the `/api/*` routes.
- Open the web client (http://localhost:5173) and provide your email in the first form. Submitting the form redirects the browser to `/oauth2/start?rd=<current_page>` with the email in `login_hint`.
- After completing the upstream login, oauth2-proxy forwards identity headers (`X-Auth-Request-Email`, `X-Auth-Request-User`, etc.) to the backend.
- The login panel automatically calls `POST /api/auth/session`, which reads those headers, mints JWT/refresh tokens, and stores them in the browser via `AuthContext.setTokens`.
- Rationale: the backend now trusts oauth2-proxy as the primary identity provider instead of performing its own OTP or Google code exchange.

### Token storage snapshot
- Successful email or demo flows persist tokens through `AuthContext.setTokens`, storing `mindwell:auth` in `localStorage` and mirroring state in `tokenStore`.
- Stored JSON resembles `{"accessToken":"<JWT>","refreshToken":"<opaque>","expiresAt":1700000000000}` with an epoch expiry in milliseconds.
- Clearing the entry or calling `AuthContext.clearTokens` drops authentication state immediately.

## Demo code exchange (allowlisted)
- Administrators maintain an allowlist in the JSON file referenced by `DEMO_CODE_FILE` (sample: `config/demo_codes.json`).
- Each entry supports `token_limit` (refresh-token quota) and `chat_token_quota` (chat turns before the subscription prompt). Omit `chat_token_quota` to fall back to `CHAT_TOKEN_DEMO_QUOTA`.
- Enter a permitted code in the second form on the login panel; the frontend submits `POST /api/auth/demo` with that value.
- The backend validates the code against the registry, creates (or reuses) a demo `User` record, enforces the demo token quota, and returns JWT/refresh tokens.
- Demo tokens respect `AUTH_DEMO_TOKEN_LIMIT`; exceeding the limit returns `HTTP 400` with the relevant error message.
- When chat tokens reach zero, the web client renders a subscription overlay and blocks further chat submissions until the quota is replenished.

## Resetting state
- Use the **Sign out** button in the header or clear the `mindwell:auth` key to return to the login screen.
- When experimenting with oauth2-proxy, also clear the proxy cookies (default `_oauth2_proxy`) to force a full reauthentication cycle.
