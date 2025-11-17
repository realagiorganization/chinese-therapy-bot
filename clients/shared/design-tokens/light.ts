import type { ThemeTokens } from "./types";

export const lightThemeTokens: ThemeTokens = {
  name: "light",
  colors: {
    primary: "#3F6F5C",
    primaryAccent: "#C78B9F",
    accentYellowGreen: "#E3EAA8",
    accentPinkGreen: "#F0CBC5",
    accentBlueGreen: "#B0DCDD",
    gradientTop: "#F9F3E8",
    gradientMid: "#F2ECDD",
    gradientBottom: "#BFD7C9",
    glassOverlay: "rgba(255, 255, 250, 0.76)",
    glassBorder: "rgba(255, 255, 255, 0.58)",
    surfaceBackground: "#F7F2EA",
    surfaceCard: "rgba(255, 255, 255, 0.9)",
    surfaceMuted: "#E8E2D7",
    textPrimary: "#2C2D29",
    textSecondary: "#57554F",
    borderSubtle: "rgba(47, 48, 44, 0.22)",
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
