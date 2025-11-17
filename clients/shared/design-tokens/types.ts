export type ColorTokens = {
  primary: string;
  primaryAccent: string;
  accentYellowGreen: string;
  accentPinkGreen: string;
  accentBlueGreen: string;
  gradientTop: string;
  gradientMid: string;
  gradientBottom: string;
  glassOverlay: string;
  glassBorder: string;
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
