# MindWell Mobile (React Native)

The Expo-based mobile app mirrors the web experience with native voice
interactions, offline caching, push notifications, and platform-optimized
navigation. It reuses the shared design tokens from `clients/shared/` to keep
visuals aligned with the web client.

## Capabilities
- **Authentication (`src/context/AuthContext.tsx`)**
  - SMS OTP flow (`/api/auth/sms` + `/api/auth/token`) with challenge caching,
    resend limits, and AsyncStorage persistence.
  - Google-code exchange helper (`exchangeGoogleCode`) for environments that
    expose the upstream OAuth callback. Both flows share the same JWT refresh
    logic and logout helpers.
- **Chat experience (`src/screens/ChatScreen.tsx`)**
  - Streams chat messages through `services/chat.ts`, shows therapist
    recommendations, and stores transcripts in AsyncStorage via `chatCache`.
  - Integrates `useVoiceInput` (Expo AV) for “press and hold” recording plus
    server-side ASR fallbacks, `useVoicePlayback` (expo-speech) for optional TTS,
    and `useVoiceSettings` for rate/pitch toggles.
  - Network resilience: `ConnectivityBanner` + `useNetworkStatus` suspend voice
    capture offline and warn the user when only cached transcripts are available.
- **Journey & Therapist surfaces**
  - `JourneyScreen` uses `useJourneyReports` to fetch `/api/reports`, groups
    conversations by date, and renders summary/transcript tabs with fallback
    data when the API has no history yet.
  - `TherapistDirectoryScreen` + `useTherapistDirectory` hydrate summaries,
    expose specialty/language/price filters, lazily fetch detail cards, and
    gracefully fall back to the local seed dataset.
- **Push notifications & performance**
  - `usePushNotifications` registers Expo push tokens, caches them for seven
    days, and reuses them per user.
  - `useStartupProfiler` logs mount/interactions milestones so `docs/mobile_performance.md`
    can track regressions across devices.

## Getting Started

```bash
cd clients/mobile
npm install
npx expo doctor         # validates the toolchain
cat <<'EOF' > .env.local
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api
EXPO_PUBLIC_SPEECH_REGION=eastasia
# Optional: point to oauth2-proxy or tunneled environments as needed
EOF
npm run start           # launches Expo/Metro
```

- Use `npm run ios` / `npm run android` when a simulator/emulator is available.
- When oauth2-proxy is not running you can target the FastAPI origin directly,
  but only the SMS/Google flows defined in the mobile app will function.
- For physical devices ensure the API base URL is reachable over the network
  (tunnel via `ngrok`/`expo tunnel` if needed).

## Scripts

| Command | Description |
| --- | --- |
| `npm run start` | Expo dev server with QR codes for devices/simulators. |
| `npm run ios` / `npm run android` | Build and launch the native runtime via Expo. |
| `npm run lint` | ESLint (uses `eslint-config-universe`). |
| `npm run typecheck` | TypeScript project references for `src/`. |
| `npm run build:release` | `expo export` multi-platform bundle with sourcemaps. |
| `npm run profile:android` | Produces a profiled Android build under `dist/profile-android/`. |
| `npm run optimize:assets` | Compresses image/audio assets via `expo optimize`. |

## Architecture Notes

- `src/context/` – AuthContext (tokens, OTP state) and VoiceSettingsContext (rate,
  pitch, enable toggle).
- `src/hooks/` – Voice input/playback, push notifications, journey reports,
  network status, therapist directory, startup profiling.
- `src/services/` – Thin API wrappers for auth/chat/reports/therapists/voice +
  push notification helpers.
- `src/screens/` – Login, Chat, Journey, Therapist Directory shells used by the
  tab bar inside `App.tsx`.
- `src/components/ConnectivityBanner.tsx` – Shared offline banner reused across
  screens.
- `src/theme/ThemeProvider.tsx` – Consumes `clients/shared/design-tokens` so
  spacing/radius/color primitives match the web client.

## Voice & Push Details

- `useVoiceInput` relies on Expo AV to start/stop recordings, writes temp files
  via `expo-file-system`, converts them to `Blob`s, and posts them to
  `/api/voice/transcribe`. Errors are localized and rendered inline by the chat
  composer.
- `useVoicePlayback` slices assistant replies into sentence-level segments and
  speaks them via `expo-speech`, honoring the rate/pitch settings stored in
  AsyncStorage.
- `usePushNotifications` caches Expo push tokens (`@mindwell/mobile/push-token`)
  and refreshes them lazily if the user/logged-in status changes.

## Offline & Error Handling

- `services/chatCache.ts` stores session ID, transcript, therapist
  recommendations, and memory highlights per user so the chat screen can render
  instantly when the app relaunches offline.
- `useNetworkStatus` polls Expo Network APIs and wakes up whenever the app
  returns to the foreground, ensuring UI state reflects reality.
- Most services include fallback datasets (journey summaries, therapist cards)
  so QA and demo flows remain functional without a live backend.
