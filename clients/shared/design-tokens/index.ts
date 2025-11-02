export * from "./types";
export { lightThemeTokens } from "./light";

export const availableThemes = {
  light: "light"
} as const;

export type AvailableThemeKey = keyof typeof availableThemes;
