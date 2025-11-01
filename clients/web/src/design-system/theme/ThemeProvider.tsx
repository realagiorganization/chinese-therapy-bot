import { useEffect } from "react";
import type { ReactNode } from "react";

import { lightTheme, tokensToCssVariables } from "./tokens";
import type { ThemeTokens } from "./tokens";

type ThemeProviderProps = {
  children: ReactNode;
  theme?: ThemeTokens;
};

export function ThemeProvider({ children, theme = lightTheme }: ThemeProviderProps) {
  useEffect(() => {
    const variables = tokensToCssVariables(theme);
    const root = document.documentElement;
    Object.entries(variables).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    root.style.setProperty("--surface-background", theme.colors.surfaceBackground);
    root.style.setProperty("--text-primary", theme.colors.textPrimary);
    root.style.setProperty("--text-secondary", theme.colors.textSecondary);
    root.style.setProperty("--surface-card", theme.colors.surfaceCard);
    root.style.setProperty("--surface-muted", theme.colors.surfaceMuted);

    return () => {
      Object.keys(variables).forEach((key) => root.style.removeProperty(key));
    };
  }, [theme]);

  return <>{children}</>;
}
