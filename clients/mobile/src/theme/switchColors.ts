import type { Theme } from "./ThemeProvider";

type SwitchColors = {
  trackTrue: string;
  trackFalse: string;
  thumbTrue: string;
  thumbFalse: string;
  iosFalse: string;
};

/**
 * Returns the shared palette for toggle switches so the Messenger-inspired
 * outlined aesthetic stays consistent across screens.
 */
export function getAcademicSwitchColors(theme: Theme): SwitchColors {
  return {
    trackTrue: "rgba(52, 92, 77, 0.45)",
    trackFalse: "rgba(44, 45, 41, 0.18)",
    thumbTrue: theme.colors.primary,
    thumbFalse: theme.colors.surfaceCard,
    iosFalse: "rgba(44, 45, 41, 0.18)",
  };
}
