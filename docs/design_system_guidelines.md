# MindWell Design System Usage Guidelines

This guide documents how the shared MindWell design tokens should be consumed across React web and future React Native/mobile clients. The goal is to maintain Mandarin-first UX decisions while ensuring component parity.

## Token Source of Truth
- **Location:** `clients/shared/design-tokens/`
- **Exports:** TypeScript (`index.ts`, `light.ts`) and a serialized JSON snapshot (`tokens.json`)
- **Structure:** Color, typography, spacing, border radius, and shadow tokens aligned with the MindWell brand palette.

### Consumption Patterns
- **React (web):** Import `lightThemeTokens` (or future variants) and feed them into the web-specific `ThemeProvider`, which converts tokens to CSS variables.
- **React Native/mobile:** Consume the same tokens directly from the shared TypeScript module or load the snapshot JSON to hydrate style dictionaries.
- **Non-TypeScript clients:** Use `tokens.json` as a canonical reference when implementing native styling kits.

## Token Conventions
- Colors favor accessible contrast with Mandarin-friendly typography defaults (`Noto Sans SC` for headings).
- Spacing tokens are expressed in pixels to map cleanly to CSS and React Native `dp`.
- Shadow tokens use subtle depth to support calm UI states; adjust per platform if native shadow APIs differ.
- Radius tokens (`sm`, `md`, `lg`, `pill`) should match chip/button treatments across all surfaces.

## Theming Workflow
1. Import shared tokens:
   ```ts
   import { lightThemeTokens } from "../shared/design-tokens";
   ```
2. Web-specific providers convert tokens to CSS variables; mobile clients can map tokens to `StyleSheet` or platform equivalents.
3. When introducing a new theme (e.g., high-contrast), add it under `clients/shared/design-tokens/` and export via `availableThemes`.
4. Keep the JSON snapshot in sync when token values change so non-TypeScript consumers remain accurate.

## Localization Alignment
- The design system assumes Simplified Chinese copy as the primary locale; ensure type styles and spacing accommodate longer Traditional Chinese and English strings.
- Components that surface localized text should reference `i18n` keys rather than hard-coded strings so typographic adjustments remain centralized.
