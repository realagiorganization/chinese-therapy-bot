import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { lightThemeTokens } from "../../../shared/design-tokens";
import {
  defaultPalette,
  getPaletteById,
  paletteOptions,
  type PaletteId,
} from "./palettes";

type NumericScale = Record<string, number>;

export type ThemePalette = {
  id: PaletteId;
  labelZh: string;
  labelEn: string;
  descriptionZh: string;
  descriptionEn: string;
  recommendationSwatches: string[];
  preview: string[];
  options: Array<{
    id: PaletteId;
    labelZh: string;
    labelEn: string;
    descriptionZh: string;
    descriptionEn: string;
    preview: string[];
  }>;
  setPalette: (id: PaletteId) => void;
};

export type Theme = {
  colors: typeof lightThemeTokens.colors;
  spacing: NumericScale;
  radius: NumericScale;
  shadow: typeof lightThemeTokens.shadow;
  typography: typeof lightThemeTokens.typography;
  palette: ThemePalette;
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

const PALETTE_STORAGE_KEY = "mindwell.palette";

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [paletteId, setPaletteId] = useState<PaletteId>(defaultPalette.id);

  useEffect(() => {
    let cancelled = false;
    AsyncStorage.getItem(PALETTE_STORAGE_KEY)
      .then((stored) => {
        if (cancelled || !stored) {
          return;
        }
        setPaletteId(getPaletteById(stored).id);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePaletteChange = useCallback((nextId: PaletteId) => {
    setPaletteId(nextId);
    AsyncStorage.setItem(PALETTE_STORAGE_KEY, nextId).catch(() => undefined);
  }, []);

  const palette = useMemo(() => getPaletteById(paletteId), [paletteId]);
  const colors = useMemo(
    () => ({
      ...lightThemeTokens.colors,
      ...palette.overrides,
    }),
    [palette],
  );
  const spacingScale = useMemo(
    () => parsePxScale(lightThemeTokens.spacing),
    [],
  );
  const radiusScale = useMemo(() => parsePxScale(lightThemeTokens.radius), []);

  const theme = useMemo<Theme>(() => {
    return {
      colors,
      spacing: spacingScale,
      radius: radiusScale,
      shadow: lightThemeTokens.shadow,
      typography: lightThemeTokens.typography,
      palette: {
        id: palette.id,
        labelZh: palette.labelZh,
        labelEn: palette.labelEn,
        descriptionZh: palette.descriptionZh,
        descriptionEn: palette.descriptionEn,
        recommendationSwatches: palette.recommendationSwatches,
        preview: palette.preview,
        options: paletteOptions.map((option) => ({
          id: option.id,
          labelZh: option.labelZh,
          labelEn: option.labelEn,
          descriptionZh: option.descriptionZh,
          descriptionEn: option.descriptionEn,
          preview: option.preview,
        })),
        setPalette: handlePaletteChange,
      },
    };
  }, [colors, handlePaletteChange, palette, radiusScale, spacingScale]);

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
