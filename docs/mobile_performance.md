# Mobile Performance Playbook

Purpose: provide a repeatable process to validate iOS gestures, measure startup latency, and shrink asset footprints—directly addressing Phase 4 iOS/Android optimization items.

## 1. Gesture & Interaction Validation (iOS)

- App root now wraps a `GestureHandlerRootView` (`clients/mobile/App.tsx`), ensuring gesture-handler stacks behave consistently with Apple HIG expectations.
- Validation steps:
  1. Launch on iPhone 12/iOS 17 simulator.
  2. Verify interactive gestures:
     - Scroll transcript (momentum + bounce).
     - Swipe-to-dismiss keyboard when touching outside composer.
     - Long-press voice button without jitter.
  3. Confirm safe-area padding on notch devices.
- Log observations in `docs/testing/mobile/<date>-ios.md` (create new file per run).

## 2. Startup Instrumentation

- `useStartupProfiler` hook (`clients/mobile/src/hooks/useStartupProfiler.ts`) captures:
  - `mounted`
  - `interactions-complete`
  - `chat-cache-ready`
  - `chat-screen-visible`
  - `chat-first-response` (first assistant reply)
- Logs appear as `[StartupProfiler:shell] auth-authenticated +1234ms (ios)` etc.
- Recommended workflow:
  1. Install release build on target device.
  2. Launch app and capture device logs (`npx expo run:ios --device` or `adb logcat`).
  3. Record timings in spreadsheet to track regressions. Aim for <1200 ms to `chat-screen-visible` on iPhone 12 and <2000 ms on Redmi Note 11.

## 3. Android Bundle & Asset Budget

- Script `scripts/mobile-profile-android.sh` generates a release bundle and reports raw/gzip sizes.
  ```bash
  cd clients/mobile
  npm run profile:android
  ```
- Output example:
  ```
  Bundle (raw): 512345 bytes
  Bundle (gzip): 182345 bytes
  Assets (raw): 2839012 bytes
  Assets (gzip): 903456 bytes
  ```
- Tracking:
  - Keep gzip bundle <2.5 MB to support mid-range devices (Helio G95 tier).
  - Log numbers in `docs/testing/mobile/<date>-android.md`.

## 4. Asset Optimization

- Run `npm run optimize:assets` after adding new imagery/audio.
- Commit optimized assets and include summary of before/after sizes in PR description.
- Pair with bundle profiling to ensure cumulative savings.

## 5. Regression Gates

- Add CI step once secrets are available to execute `npm run profile:android` in nightly pipeline and publish sizes to build summary.
- Future work: wire `useStartupProfiler` events into telemetry (App Insights) via custom endpoints for automated trend tracking.

## Validation Log – 2025-11-02

### iOS Gesture & Interaction Checklist

- Verified `clients/mobile/App.tsx` wraps the app in `GestureHandlerRootView` and `SafeAreaProvider`, matching Apple HIG requirements for edge gestures.
- Confirmed haptic feedback triggers (`expo-haptics`) fire on the voice input press handlers in `clients/mobile/src/screens/ChatScreen.tsx:486`.
- Ensured connectivity banner gracefully handles offline states with safe-area padding (`clients/mobile/src/components/ConnectivityBanner.tsx:1-160`).
- Pending: hands-on simulator run to capture physical interaction notes (schedule during next QA window).

### Android Bundle Profiling

- Command: `cd clients/mobile && npm run profile:android` (invokes `scripts/mobile-profile-android.sh`).
- Output on 2025-11-02:
  - `index.android.bundle` raw size: **1,393,439 bytes**
  - `index.android.bundle` gzip size: **352,949 bytes**
  - Asset payload: **0 bytes** (no bundled assets detected during profiling run)
- Bundled artefacts stored under `clients/mobile/dist/profile-android/` for review.
- Action items: integrate metro alias warning follow-up (migrate to `@react-native/metro-config` once Expo template supports it) and automate bundle budget alerts in CI.
