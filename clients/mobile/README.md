# MindWell Mobile (React Native)

This directory contains the Expo-based React Native client that mirrors the web experience while targeting iOS and Android. The mobile app currently delivers:

- SMS OTP and Google authorization flows sharing backend endpoints.
- Chat UI wired to the FastAPI `/api/chat/message` endpoint with therapist recommendations and memory highlights surfaced inline.
- Offline transcript restoration backed by AsyncStorage so recent sessions remain available without connectivity.
- Push notification scaffolding (Expo Notifications) that registers device tokens once the user authenticates.
- Shared theming sourced from `clients/shared/design-tokens` to maintain brand consistency across platforms.

## Getting Started

1. Install dependencies from the repository root:
   ```bash
   cd clients/mobile
   npm install
   ```
2. Provide the required environment variables (see `ENVS.md`):
   ```bash
   export EXPO_PUBLIC_API_BASE_URL="http://localhost:8000/api"
   ```
3. Launch the Expo development server:
   ```bash
   npm run start
   ```

## Project Structure

- `App.tsx`: Composes the auth provider, theme provider, and root navigation shell.
- `src/context/AuthContext.tsx`: Persists token state with AsyncStorage and orchestrates login flows.
- `src/screens/LoginScreen.tsx`: SMS + Google login UX with Mandarin-first copy.
- `src/screens/ChatScreen.tsx`: Chat transcript presentation, therapist recommendations, and message composer.
- `src/services/`: Thin API client abstractions for authentication and chat endpoints.

## Next Steps

- Ship Android voice input parity and performance profiling automation.
- Wire Google/Apple OAuth SDKs for device-native authorization codes.

## Release Bundles

- `npm run build:release` executes `expo export` (see `metro.config.js` for shared workspace resolution) and writes artefacts to `build/release/`.
- The GitHub Actions workflow `release.yml` packages the export output (`mobile-release` artefact) alongside backend/web bundles for staging or production promotion.
