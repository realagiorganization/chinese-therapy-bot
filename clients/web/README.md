# MindWell Web Client (Phase 4 Scaffold)

This package introduces the initial Phase 4 groundwork for the MindWell Mandarin-first experience. It focuses on two deliverables called out in `DEV_PLAN.md`:

1. **Shared Design System** – Theme tokens, foundational components (Button, Card, Typography), and a CSS-variable powered theme provider tuned for Chinese typography.
2. **Localization Framework** – `i18next` + `react-i18next` bootstrap with Simplified Chinese as the primary locale and English fallback.

## Commands

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Lint & test
pnpm lint
pnpm test
```

> The project uses Vite + React 18 and Vitest. See `vite.config.ts` for the unit test configuration and `src/design-system/` for the tokens/components library.

## Next Steps

- Expand the component set (inputs, layout primitives, chat bubbles) and extract to a reusable package for the mobile client.
- Wire API data sources once backend endpoints are reachable.
- Introduce visual regression testing (Chromatic/Storybook) after stabilising core components.
