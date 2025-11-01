# MindWell Release Management Handbook

This guide expands the DEV_PLAN release tasks by codifying how we cut releases, manage store submissions, and coordinate QA. Use it as the baseline playbook for App Store/TestFlight and Android beta launches.

## Branching & Versioning

- **Main** remains the integration branch gated by CI.
- **Release branches** follow `release/<platform>-<YYYYMMDD>`. Cut from `main` once the sprint scope is code-complete.
- **Hotfix branches** target `release/*` when fixes are required during review. Merge back into both the release branch and `main`.
- **Versioning**
  - Backend/web: semantic versioning `MAJOR.MINOR.PATCH`.
  - Mobile: keep `app.config.ts` `version` in sync with semantic version and bump `ios.buildNumber` / `android.versionCode` monotonically.
  - Tag every production release as `vMAJOR.MINOR.PATCH` and annotate with changelog highlights.

## iOS Submission Checklist

1. **Pre-flight QA**
   - Run `npm run lint`, `npm run typecheck`, `npm run profile:android` for parity metrics, and manual smoketests on iPhone 12 / iPhone SE simulators.
   - Capture in-app screenshots (5.5", 6.5", iPad if we ever enable tablet target).
2. **Build & Archive**
   - `expo prebuild --clean`, then `expo run:ios --configuration Release`.
   - Validate App Store assets: icons, splash, permissions copy (`infoPlist` already configured for notifications + background modes).
3. **TestFlight**
   - Upload via Transporter or `eas submit --platform ios --profile app-store`.
   - Add release notes summarizing therapist browsing, summaries dashboard, and voice input improvements.
4. **App Store Metadata**
   - Localized description (zh-CN primary, en-US secondary), privacy policy link, keywords.
   - Fill in content rights and data collection questionnaires referencing `docs/data_governance.md`.
5. **Approval & Rollout**
   - Flag the `release/ios-*` branch for `Monitoring Agent` to watch post-launch metrics.

## Android Beta Checklist

1. **Performance Profiling**
   - `npm run profile:android` to capture bundle + asset sizes; target <2.5 MB gzip bundle, <8 MB assets for mid-range device cold start.
   - Review profiler output in CI summary (`scripts/mobile-profile-android.sh` prints raw/gzip sizes).
   - Run on physical Redmi Note 11 or similar using `expo run:android --variant release` and collect startup timing logs (from `useStartupProfiler`).
2. **Bundle Generation**
   - `expo prebuild --clean`, `expo run:android --variant release`.
   - Verify `android/app/src/main/AndroidManifest.xml` permissions (recording audio, internet) and adaptive icons.
3. **Play Console Upload**
   - Sign the AAB through Gradle (managed by Expo) and upload to closed testing track.
   - Complete Data safety and content rating forms referencing privacy policy.
4. **Release Notes & Reviewers**
   - Document changes in `docs/changelog.md` (create per-release section) and share with QA + stakeholder mailing lists.

## Changelog & Communication

- Maintain `docs/changelog.md`; include date, version, key highlights, and regression risks.
- Announce release candidates in Slack `#mindwell-release` with:
  - Release branch/tag
  - QA owner
  - Target submission date
  - Links to bundle size report and profiling logs

## Incident & Rollback Handling

- If blocking defects arise post-rollout:
  1. Create hotfix branch (`hotfix/<platform>-<issue>`).
  2. Reproduce and land fix with targeted QA.
  3. Submit expedited review (iOS) or staged rollout (Android) while notifying `Monitoring Agent`.
- Maintain rollback decision logs in `docs/incidents/YYYY-MM-DD-<slug>.md`.
