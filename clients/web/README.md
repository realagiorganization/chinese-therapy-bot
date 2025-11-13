# MindWell Web Client

The Vite/React application is the reference interface for oauth2-proxy sessions,
demo-code onboarding, streaming chat, therapist discovery, journey insights, and
Explore modules. It shares the design system tokens under `clients/shared/` so
visual primitives match the Expo mobile app.

## Capabilities
- **Authentication panel** – `src/components/LoginPanel.tsx` handles both
  oauth2-proxy handoffs (session exchange via `POST /api/auth/session`) and
  demo-code login. Tokens live in `AuthContext` + `localStorage`, and the helper
  `api/tokenStore.ts` keeps fetch headers in sync.
- **Chat panel** – `src/components/ChatPanel.tsx` streams SSE responses through
  `useChatSession`. It renders therapist recommendations, memory highlights, and
  template quick-start chips, and downgrades to non-streamed replies when the
  SSE connection drops. MediaRecorder + the server-side ASR hook are exposed via
  `useServerTranscriber`, while the fallback speech-recognition path uses the
  browser APIs directly.
- **Voice & transcription** – microphone capture pipes blobs to
  `/api/voice/transcribe`. The hook automatically clears errors, cancels active
  recordings, and displays localized errors defined in `src/i18n`.
- **Journey dashboard & Explore modules** – `JourneyDashboard` and
  `ExploreModules` consume `/api/reports` and `/api/explore/modules`, surface
  fallback data when the backend is empty, and render flag status badges so ops
  engineers can verify rollout state.
- **Therapist directory** – `TherapistDirectory` + `useTherapistDirectory`
  synchronize filters with `/api/therapists`, fall back to seed data when the
  API is unreachable, and fetch detail cards lazily via `loadTherapistDetail`.

## Getting Started

```bash
cd clients/web
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
echo "VITE_AUTH_PROXY_BASE_URL=http://localhost:4180" >> .env.local
npm run dev
```

- `VITE_API_BASE_URL` must point at the FastAPI origin (`/api` routes are
  appended automatically).
- `VITE_AUTH_PROXY_BASE_URL` should match the oauth2-proxy origin; omit it if
  the proxy and backend share the same host.
- The dev server proxies unauthenticated calls when possible. Protected routes
  still require valid JWTs or an oauth2-proxy session cookie.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start Vite in dev mode with hot module reload. |
| `npm run lint` | ESLint + TypeScript lint (configured in `package.json`). |
| `npm run test` | Vitest suite (component/unit tests under `src`). |
| `npm run build` | Production build (Vite) used by CI and Azure Static Web Apps. |
| `npm run preview` | Serve the production bundle locally for smoke tests. |

## Project Structure

- `src/api/` – Thin fetch wrappers (`chat.ts`, `auth.ts`, `reports.ts`, etc.),
  including SSE parsing and fallback payloads.
- `src/auth/` – Auth context, token persistence helpers, and interceptors.
- `src/components/` – Page-level components (ChatPanel, LoginPanel,
  JourneyDashboard, ExploreModules, TherapistDirectory, LocaleSwitcher).
- `src/hooks/` – State machines for chat sessions, templates, explore modules,
  journey reports, therapist directory filters, and voice transcription.
- `src/design-system/` – Button/Card/Typography primitives backed by the shared
  token set in `clients/shared/design-tokens`.
- `src/i18n/` – `i18next` configuration with Simplified Chinese primary copy
  plus English/Russian fallbacks.

## Voice & Streaming Notes

- SSE parsing lives in `api/chat.ts` (`streamChatTurn`). The hook merges server
  events (`session`, `token`, `complete`, `error`) and gracefully degrades to a
  single `process_turn` call if the stream aborts.
- `useServerTranscriber` chooses the best MediaRecorder MIME type the browser
  supports and posts blobs to `/api/voice/transcribe`; if the API returns a
  `503` it shows a localized "server ASR unavailable" message so users can fall
  back to manual typing.
- Voice input controls are disabled automatically when the browser lacks media
  APIs or when the auth context does not have a valid JWT.
