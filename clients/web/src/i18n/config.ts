import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enUS from "../locales/en-US.json";
import zhCN from "../locales/zh-CN.json";
import zhTW from "../locales/zh-TW.json";
import ruRU from "../locales/ru-RU.json";

const resources = {
  "zh-CN": { translation: zhCN },
  "zh-TW": { translation: zhTW },
  "en-US": { translation: enUS },
  "ru-RU": { translation: ruRU }
} satisfies Record<string, { translation: Record<string, unknown> }>;

const SUPPORTED_CODES = Object.keys(resources);
const LOCALE_STORAGE_KEY = "mindwell:locale";

const FALLBACK_MAP: Record<string, string[]> & { default: string[] } = {
  "zh-CN": ["zh-CN", "en-US"],
  "zh-TW": ["zh-TW", "zh-CN", "en-US"],
  "en-US": ["en-US", "zh-CN"],
  "ru-RU": ["ru-RU", "en-US", "zh-CN"],
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

function normalizeLocale(code: string | null | undefined): string | null {
  if (!code) {
    return null;
  }
  const match = SUPPORTED_CODES.find((supported) => supported.toLowerCase() === code.toLowerCase());
  return match ?? null;
}

function readStoredLocale(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return normalizeLocale(stored);
  } catch {
    return null;
  }
}

function detectInitialLocale(): string {
  const stored = readStoredLocale();
  if (stored) {
    return stored;
  }
  if (typeof window !== "undefined") {
    const navigatorLocales: Array<string | undefined> = Array.isArray(window.navigator?.languages)
      ? window.navigator.languages
      : [window.navigator?.language];
    for (const candidate of navigatorLocales) {
      const normalized = normalizeLocale(candidate);
      if (normalized) {
        return normalized;
      }
    }
  }
  return "zh-CN";
}

function persistLocale(code: string) {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = normalizeLocale(code);
  if (!normalized) {
    return;
  }
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, normalized);
  } catch {
    // Ignore storage failures (private mode, quota, etc.)
  }
}

const initialLocale = detectInitialLocale();

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources,
    lng: initialLocale,
    fallbackLng: fallbackFor,
    supportedLngs: SUPPORTED_CODES,
    interpolation: {
      escapeValue: false
    }
  });
} else {
  const current = normalizeLocale(i18n.resolvedLanguage ?? i18n.language);
  if (!current || current !== initialLocale) {
    void i18n.changeLanguage(initialLocale);
  }
}

const resolved = i18n.resolvedLanguage ?? i18n.language ?? initialLocale;

if (typeof document !== "undefined") {
  document.documentElement.lang = resolved;
}

persistLocale(resolved);

i18n.on("languageChanged", (language) => {
  const normalized = normalizeLocale(language) ?? language;
  if (typeof document !== "undefined") {
    document.documentElement.lang = normalized;
  }
  persistLocale(normalized);
});

export default i18n;
