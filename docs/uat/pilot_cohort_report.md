# Pilot Cohort Report — Week 46, 2025

## Cohort Overview
- Cohort tag: `pilot-2025w46`
- Participants: 5 (4 pilot participants, 1 therapist reviewer)
- Channels covered: mobile iOS, mobile Android, WeChat wrapper, and desktop web
- Reference fixtures: `docs/uat/pilot_cohort_feedback.json`

## Quantitative Snapshot
- Average sentiment: **3.6** (≥4 in 60% of entries)
- Average trust: **4.0** (≥4 in 80% of entries)
- Average usability: **3.0** (≥4 in 40% of entries)
- Follow-ups required: **3** (Iris, Jun, Mei)
- Severity mix: high (2), medium (2), low (1)
- Channel mix: mobile-iOS (2), mobile-Android (1), web (1), WeChat (1)
- Top tags: `keyboard-handoff` (2), `palette-*` variants (3 distinct), `settings-discovery`, `journey-scroll`, `quote-placement`

## Highlights
- **Iris (mobile-iOS, zh-CN):** New academic prompt + bilingual quote improves perceived gravitas and reduces the need for a greeting flourish.
- **Jun (mobile-Android, en-US):** Back arrow persists correctly when the keyboard is open, matching the Messenger reference layout.
- **Dr. Lin (web therapist view):** AI-personalized therapist recommendations align with recent pilot transcripts and surface believable rationales.
- **Bo (journey review, zh-TW):** Serif typography clarifies headings and makes the Journey screen feel more editorial.

## Blockers & Issues
1. **Navigation loss after keyboard dismissal (Android/WeChat):** Pixel 8 and WeChat wrapper can hide the four-tab navigation after the keyboard closes, requiring a restart (tags: `keyboard-handoff`, `wechat-bridge`).
2. **Voice arrow overlap (iOS zh-CN):** Voice playback arrow can shift into the send icon when the locale is toggled quickly (tag: `voice-mode`).
3. **Settings access via WeChat:** Header clipping hides the settings button, preventing palette toggling and QA verification (tag: `settings-discovery`).
4. **Therapist rationale truncation (web):** English copy truncates on 13" Safari windows, hiding rationale sentences (tag: `copy-density`).
5. **Journey gradient flicker (iOS mini devices):** Scroll bounce reveals a blank background while AsyncStorage rehydrates the palette (tag: `journey-scroll`).

## Prioritized Follow-ups
1. Patch keyboard/nav restoration across Android + WeChat webview by forcing a navigation re-measure when IME visibility changes (blocking severity-high entries).
2. Relayout voice arrow & send button container on iOS to reserve a static min-width when locale or voice mode toggles.
3. Add an alternate settings entry point in the overflow sheet for constrained headers (covers WeChat wrapper and small web heights).
4. Tighten copy wrapping for therapist rationale blocks on web (CSS clamp + multi-line ellipsis) while retaining Mandarin translations.
5. Cache gradient tokens earlier in the Journey stack to avoid flicker during tab switches on smaller devices.

## Artifacts
- Structured responses captured via `docs/uat/pilot_cohort_feedback.json`
- Database seeding utility: `services/backend/scripts/seed_pilot_feedback.py` (use `--cohort pilot-2025w46 --replace` when loading into Postgres)
- Aggregated summaries for future cohorts can continue to use `mindwell-uat-report` once the feedback entries are stored server-side.
