export type ColorTokens = {
  primary: string;
  primaryAccent: string;
  surfaceBackground: string;
  surfaceCard: string;
  surfaceMuted: string;
  textPrimary: string;
  textSecondary: string;
  borderSubtle: string;
  focusOutline: string;
  success: string;
  warning: string;
  danger: string;
};

export type TypographyTokens = {
  fontFamilyBase: string;
  fontFamilyHeading: string;
  weightRegular: number;
  weightMedium: number;
  weightSemibold: number;
  weightBold: number;
};

export type RadiusTokens = {
  sm: string;
  md: string;
  lg: string;
  pill: string;
};

export type ShadowTokens = {
  sm: string;
  md: string;
  lg: string;
};

export type SpacingTokens = {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
};

export type ThemeTokens = {
  name: string;
  colors: ColorTokens;
  typography: TypographyTokens;
  radius: RadiusTokens;
  shadow: ShadowTokens;
  spacing: SpacingTokens;
};

export const lightTheme: ThemeTokens = {
  name: "light",
  colors: {
    primary: "#3B82F6",
    primaryAccent: "#2563EB",
    surfaceBackground: "#F8FAFC",
    surfaceCard: "#FFFFFF",
    surfaceMuted: "#E2E8F0",
    textPrimary: "#0F172A",
    textSecondary: "#475569",
    borderSubtle: "rgba(15, 23, 42, 0.08)",
    focusOutline: "#2563EB",
    success: "#22C55E",
    warning: "#F59E0B",
    danger: "#EF4444"
  },
  typography: {
    fontFamilyBase:
      "\"Inter\", system-ui, -apple-system, \"BlinkMacSystemFont\", \"Segoe UI\", sans-serif",
    fontFamilyHeading: "\"Noto Sans SC\", \"Inter\", system-ui, sans-serif",
    weightRegular: 400,
    weightMedium: 500,
    weightSemibold: 600,
    weightBold: 700
  },
  radius: {
    sm: "6px",
    md: "12px",
    lg: "18px",
    pill: "999px"
  },
  shadow: {
    sm: "0 1px 3px rgba(15, 23, 42, 0.12)",
    md: "0 6px 14px rgba(15, 23, 42, 0.10)",
    lg: "0 18px 32px rgba(15, 23, 42, 0.12)"
  },
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "16px",
    lg: "24px",
    xl: "32px"
  }
};

const TOKEN_PREFIX = "--mw";

export const themeVariableMap: Record<string, string> = {
  "colors.primary": `${TOKEN_PREFIX}-color-primary`,
  "colors.primaryAccent": `${TOKEN_PREFIX}-color-primary-accent`,
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
