import { createContext, ReactNode, useContext, useMemo } from "react";

import { lightThemeTokens } from "../../../shared/design-tokens";

type NumericScale = Record<string, number>;

export type Theme = {
  colors: typeof lightThemeTokens.colors;
  spacing: NumericScale;
  radius: NumericScale;
  shadow: typeof lightThemeTokens.shadow;
  typography: typeof lightThemeTokens.typography;
};

const ThemeContext = createContext<Theme | null>(null);

function parsePxScale(scale: Record<string, string>): NumericScale {
  const entries = Object.entries(scale).map(([key, value]) => {
    const parsed = Number.parseFloat(value.replace("px", "").trim());
    return [key, Number.isFinite(parsed) ? parsed : 0];
  });
  return Object.fromEntries(entries);
}

type ThemeProviderProps = {
  children: ReactNode;
};

export function ThemeProvider({ children }: ThemeProviderProps) {
  const theme = useMemo<Theme>(() => {
    return {
      colors: lightThemeTokens.colors,
      spacing: parsePxScale(lightThemeTokens.spacing),
      radius: parsePxScale(lightThemeTokens.radius),
      shadow: lightThemeTokens.shadow,
      typography: lightThemeTokens.typography,
    };
  }, []);

  return (
    <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): Theme {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider.");
  }
  return ctx;
}
