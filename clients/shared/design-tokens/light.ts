import type { ThemeTokens } from "./types";

export const lightThemeTokens: ThemeTokens = {
  name: "light",
  colors: {
    primary: "#4A9079",
    primaryAccent: "#E08DA5",
    accentYellowGreen: "#DDE59B",
    accentPinkGreen: "#F4C6C3",
    accentBlueGreen: "#A6D8D4",
    gradientTop: "#FDF6ED",
    gradientMid: "#F3EEE3",
    gradientBottom: "#D7E6D5",
    glassOverlay: "rgba(255, 255, 252, 0.82)",
    glassBorder: "rgba(255, 255, 255, 0.48)",
    surfaceBackground: "#F6F1E6",
    surfaceCard: "rgba(255, 255, 255, 0.92)",
    surfaceMuted: "#E8E0D4",
    textPrimary: "#2F302C",
    textSecondary: "#5E5B56",
    borderSubtle: "rgba(47, 48, 44, 0.18)",
    focusOutline: "#4A9079",
    success: "#3E8C64",
    warning: "#E0A84C",
    danger: "#D3574B"
  },
  typography: {
    fontFamilyBase:
      "\"Georgia\", \"Times New Roman\", \"Noto Serif SC\", serif",
    fontFamilyHeading:
      "\"Times New Roman\", \"Georgia\", \"Noto Serif SC\", serif",
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
