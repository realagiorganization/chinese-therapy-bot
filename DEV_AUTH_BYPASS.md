# Developer Auth Bypass

## Google OAuth sandbox flow
- Open the web client (http://localhost:5173) and choose **Google sign-in (dev sandbox)**.
- Enter any non-empty string (e.g. `demo-oauth-code`) into the authorization code field.
- Submit the form; the frontend sends a `POST http://localhost:8000/api/auth/token` payload of `{"provider":"google","code":"<your value>"}`.
- The backend responds with a synthetic token pair via `AuthService.exchange_token`, after which the app unlocks and the frontend persists the pair.
- Rationale: the local backend uses the stubbed `GoogleOAuthClient`, which hashes whatever code you supply and returns a synthetic Google profile without an external exchange (`services/backend/app/integrations/google.py`).

### Token storage snapshot
- Successful Google or SMS flows end up in `AuthContext.setTokens`, which writes a single `localStorage` entry `mindwell:auth`.
- The stored JSON looks like `{"accessToken":"<JWT>","refreshToken":"<opaque string>","expiresAt":1700000000000}`; `expiresAt` is a UTC epoch in milliseconds.
- Tokens are also mirrored in the in-memory `tokenStore` module so API calls can attach the bearer header.

### Troubleshooting the Google sandbox
- Seeing **Not found** under the form means the `/api/auth/token` request returned HTTP 404 instead of the token payload.
- Verify the backend dev server is running on port `8000` and that `VITE_API_BASE_URL` (if set) still points at that origin.
- Keep `VITE_API_BASE_URL` as `http://localhost:8000` (no trailing `/api`); the web client already appends `/api/auth/...`, so including `/api` twice produces the 404s (`/api/api/auth/*`).
- FastAPI mounts the auth routes under `/api/auth/*` (`services/backend/app/api/router.py`); a different base URL or stale proxy configuration will lead to the 404 response.

## SMS OTP flow (optional)
- Start the backend; in local mode it instantiates `ConsoleSMSProvider`.
- Request an SMS code in the login panel. The generated OTP is printed in the backend logs (`[SMS] Dispatching OTP ...`).
- Enter the logged code to complete login if you prefer testing the SMS path.
- Provider wiring lives in `services/backend/app/api/deps.py`, which selects the console provider when Twilio credentials are absent.

## Resetting state
- Use the **Sign out** button in the header or clear `localStorage` key `mindwell:auth` to return to the login screen when needed.
