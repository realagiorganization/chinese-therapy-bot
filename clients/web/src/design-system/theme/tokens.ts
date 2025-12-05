import type { ThemeTokens } from "../../../../shared/design-tokens";
import { availableThemes, lightThemeTokens } from "../../../../shared/design-tokens";

export type { ThemeTokens };

export const lightTheme: ThemeTokens = lightThemeTokens;
export { availableThemes };

const TOKEN_PREFIX = "--mw";

export const themeVariableMap: Record<string, string> = {
  "colors.primary": `${TOKEN_PREFIX}-color-primary`,
  "colors.primaryAccent": `${TOKEN_PREFIX}-color-primary-accent`,
  "colors.accentYellowGreen": `${TOKEN_PREFIX}-color-accent-yellow-green`,
  "colors.accentPinkGreen": `${TOKEN_PREFIX}-color-accent-pink-green`,
  "colors.accentBlueGreen": `${TOKEN_PREFIX}-color-accent-blue-green`,
  "colors.gradientTop": `${TOKEN_PREFIX}-gradient-top`,
  "colors.gradientMid": `${TOKEN_PREFIX}-gradient-mid`,
  "colors.gradientBottom": `${TOKEN_PREFIX}-gradient-bottom`,
  "colors.glassOverlay": `${TOKEN_PREFIX}-glass-overlay`,
  "colors.glassBorder": `${TOKEN_PREFIX}-glass-border`,
  "colors.surfaceBackground": `${TOKEN_PREFIX}-surface-background`,
  "colors.surfaceCard": `${TOKEN_PREFIX}-surface-card`,
  "colors.surfaceMuted": `${TOKEN_PREFIX}-surface-muted`,
  "colors.textPrimary": `${TOKEN_PREFIX}-text-primary`,
  "colors.textSecondary": `${TOKEN_PREFIX}-text-secondary`,
  "colors.borderSubtle": `${TOKEN_PREFIX}-border-subtle`,
  "colors.focusOutline": `${TOKEN_PREFIX}-focus-outline`,
  "colors.success": `${TOKEN_PREFIX}-color-success`,
  "colors.warning": `${TOKEN_PREFIX}-color-warning`,
  "colors.danger": `${TOKEN_PREFIX}-color-danger`,
  "typography.fontFamilyBase": `${TOKEN_PREFIX}-font-base`,
  "typography.fontFamilyHeading": `${TOKEN_PREFIX}-font-heading`,
  "typography.weightRegular": `${TOKEN_PREFIX}-font-weight-regular`,
  "typography.weightMedium": `${TOKEN_PREFIX}-font-weight-medium`,
  "typography.weightSemibold": `${TOKEN_PREFIX}-font-weight-semibold`,
  "typography.weightBold": `${TOKEN_PREFIX}-font-weight-bold`,
  "radius.sm": `${TOKEN_PREFIX}-radius-sm`,
  "radius.md": `${TOKEN_PREFIX}-radius-md`,
  "radius.lg": `${TOKEN_PREFIX}-radius-lg`,
  "radius.pill": `${TOKEN_PREFIX}-radius-pill`,
  "shadow.sm": `${TOKEN_PREFIX}-shadow-sm`,
  "shadow.md": `${TOKEN_PREFIX}-shadow-md`,
  "shadow.lg": `${TOKEN_PREFIX}-shadow-lg`,
  "spacing.xs": `${TOKEN_PREFIX}-spacing-xs`,
  "spacing.sm": `${TOKEN_PREFIX}-spacing-sm`,
  "spacing.md": `${TOKEN_PREFIX}-spacing-md`,
  "spacing.lg": `${TOKEN_PREFIX}-spacing-lg`,
  "spacing.xl": `${TOKEN_PREFIX}-spacing-xl`
};

export function tokensToCssVariables(theme: ThemeTokens): Record<string, string> {
  const entries: Record<string, string> = {};
  const flatten = (obj: Record<string, unknown>, path: string[] = []) => {
    Object.entries(obj).forEach(([key, value]) => {
      const nextPath = [...path, key];
      if (value && typeof value === "object") {
        flatten(value as Record<string, unknown>, nextPath);
        return;
      }
      const ref = themeVariableMap[nextPath.join(".")];
      if (ref) {
        entries[ref] = String(value);
      }
    });
  };

  flatten(theme as unknown as Record<string, unknown>);
  return entries;
}
