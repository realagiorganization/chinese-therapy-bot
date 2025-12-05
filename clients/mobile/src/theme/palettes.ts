import { lightThemeTokens } from "shared/design-tokens";

export type PaletteId = "sunlit" | "orchid" | "lagoon";

export type PaletteOption = {
  id: PaletteId;
  labelZh: string;
  labelEn: string;
  descriptionZh: string;
  descriptionEn: string;
  overrides: Partial<typeof lightThemeTokens.colors>;
  recommendationSwatches: string[];
  preview: string[];
};

const defaultOverlay = lightThemeTokens.colors.glassOverlay;
const defaultBorder = lightThemeTokens.colors.glassBorder;

export const paletteOptions: PaletteOption[] = [
  {
    id: "sunlit",
    labelZh: "黄绿调",
    labelEn: "Sunlit Grove",
    descriptionZh: "柔和黄绿搭配，底部渐变更偏暖色，贴近样稿。",
    descriptionEn:
      "Soft yellow–green tones with a warm base gradient inspired by the mock.",
    overrides: {
      gradientBottom: "#C9DDBF",
      gradientMid: "#EFE8D8",
      gradientTop: "#FCF8F2",
      accentYellowGreen: "#DCE8BF",
      accentPinkGreen: "#EEDCD5",
      accentBlueGreen: "#CFE7D7",
      glassOverlay: defaultOverlay,
      glassBorder: defaultBorder,
    },
    recommendationSwatches: [
      "rgba(218, 231, 192, 0.55)",
      "rgba(238, 221, 214, 0.55)",
      "rgba(207, 228, 214, 0.55)",
    ],
    preview: ["#C9DDBF", "#EFE8D8", "#FCF8F2"],
  },
  {
    id: "orchid",
    labelZh: "粉绿调",
    labelEn: "Orchid Study",
    descriptionZh: "粉色与翡翠绿互补，带来更明显的粉绿玻璃感。",
    descriptionEn:
      "Muted rose + emerald pairing for the requested pink–green glass aesthetic.",
    overrides: {
      gradientBottom: "#DABEC2",
      gradientMid: "#F2E5E0",
      gradientTop: "#FCF7F3",
      accentYellowGreen: "#E4EFD7",
      accentPinkGreen: "#F2D6DB",
      accentBlueGreen: "#D6E8E3",
      glassOverlay: "rgba(255, 250, 246, 0.9)",
      glassBorder: "rgba(255, 255, 255, 0.65)",
    },
    recommendationSwatches: [
      "rgba(241, 212, 218, 0.55)",
      "rgba(222, 240, 227, 0.55)",
      "rgba(233, 221, 207, 0.55)",
    ],
    preview: ["#DABEC2", "#F2E5E0", "#FCF7F3"],
  },
  {
    id: "lagoon",
    labelZh: "蓝绿调",
    labelEn: "Lagoon Field",
    descriptionZh: "蓝绿底色更清爽，顶部仍然过渡到米白色。",
    descriptionEn:
      "Blue–green footing for a calmer feel while still fading to warm beige.",
    overrides: {
      gradientBottom: "#B6D9D1",
      gradientMid: "#E3F0E9",
      gradientTop: "#FCF8F4",
      accentYellowGreen: "#E3EDC9",
      accentPinkGreen: "#EEDBD6",
      accentBlueGreen: "#BFDCD4",
      glassOverlay: "rgba(255, 255, 252, 0.9)",
      glassBorder: "rgba(255, 255, 255, 0.7)",
    },
    recommendationSwatches: [
      "rgba(191, 220, 212, 0.55)",
      "rgba(229, 240, 228, 0.55)",
      "rgba(242, 231, 216, 0.55)",
    ],
    preview: ["#B6D9D1", "#E3F0E9", "#FCF8F4"],
  },
];

export const defaultPalette = paletteOptions[0];

export function getPaletteById(id: string | null | undefined) {
  return paletteOptions.find((option) => option.id === id) ?? defaultPalette;
}
