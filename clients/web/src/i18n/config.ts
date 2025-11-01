import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enUS from "../locales/en-US.json";
import zhCN from "../locales/zh-CN.json";
import zhTW from "../locales/zh-TW.json";

const resources = {
  "zh-CN": { translation: zhCN },
  "zh-TW": { translation: zhTW },
  "en-US": { translation: enUS }
} satisfies Record<string, { translation: Record<string, unknown> }>;

const FALLBACK_MAP: Record<string, string[]> & { default: string[] } = {
  "zh-CN": ["zh-CN", "en-US"],
  "zh-TW": ["zh-TW", "zh-CN", "en-US"],
  "en-US": ["en-US", "zh-CN"],
  default: ["zh-CN", "en-US"]
};

function fallbackFor(code: string): string[] {
  if (!code) {
    return FALLBACK_MAP.default;
  }
  const normalized = code.toUpperCase();
  const explicit = Object.keys(FALLBACK_MAP).find((key) => key.toUpperCase() === normalized);
  return explicit ? FALLBACK_MAP[explicit] : FALLBACK_MAP.default;
}

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources,
    lng: "zh-CN",
    fallbackLng: fallbackFor,
    supportedLngs: Object.keys(resources),
    interpolation: {
      escapeValue: false
    }
  });
}

const resolved = i18n.resolvedLanguage ?? i18n.language ?? "zh-CN";

if (typeof document !== "undefined") {
  document.documentElement.lang = resolved;
  i18n.on("languageChanged", (language) => {
    document.documentElement.lang = language;
  });
}

export default i18n;
