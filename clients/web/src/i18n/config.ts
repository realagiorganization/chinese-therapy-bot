import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { getApiBaseUrl, withAuthHeaders } from "../api/client";
import enUS from "../locales/en-US.json";

const BASE_LOCALE = "en-US";
const SUPPORTED_CODES = ["en-US", "zh-CN", "zh-TW", "ru-RU"] as const;
const DEFAULT_LOCALE: SupportedLocale = "zh-CN";

type SupportedLocale = (typeof SUPPORTED_CODES)[number];
type TranslationFlatMap = Record<string, string>;

interface TranslationBatchResponse {
  target_locale: string;
  source_locale: string;
  translations: TranslationFlatMap;
}

const resources = {
  [BASE_LOCALE]: { translation: enUS }
} satisfies Record<string, { translation: Record<string, unknown> }>;

const LOCALE_STORAGE_KEY = "mindwell:locale";
const pendingLocaleLoads = new Map<SupportedLocale, Promise<void>>();
const baseTranslations = flattenResource(enUS as Record<string, unknown>);
const translationEntries = Object.entries(baseTranslations).map(([key, text]) => ({ key, text }));

const FALLBACK_MAP: Record<string, SupportedLocale[]> & { default: SupportedLocale[] } = {
  "zh-CN": ["zh-CN", BASE_LOCALE],
  "zh-TW": ["zh-TW", "zh-CN", BASE_LOCALE],
  "ru-RU": ["ru-RU", BASE_LOCALE],
  "en-US": [BASE_LOCALE],
  default: [BASE_LOCALE]
};

function fallbackFor(code: string): SupportedLocale[] {
  if (!code) {
    return FALLBACK_MAP.default;
  }
  const normalized = code.toUpperCase();
  const explicit = Object.keys(FALLBACK_MAP).find((key) => key.toUpperCase() === normalized);
  return explicit ? FALLBACK_MAP[explicit] : FALLBACK_MAP.default;
}

function normalizeLocale(code: string | null | undefined): SupportedLocale | null {
  if (!code) {
    return null;
  }
  const match = SUPPORTED_CODES.find((supported) => supported.toLowerCase() === code.toLowerCase());
  return match ?? null;
}

function readStoredLocale(): SupportedLocale | null {
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

function detectInitialLocale(): SupportedLocale {
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
  return DEFAULT_LOCALE;
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

async function ensureLocaleResources(locale: string | null | undefined): Promise<void> {
  const normalized = normalizeLocale(locale);
  if (!normalized || normalized === BASE_LOCALE) {
    return;
  }
  if (typeof window === "undefined") {
    return;
  }
  if (i18n.hasResourceBundle(normalized, "translation")) {
    return;
  }
  const inflight = pendingLocaleLoads.get(normalized);
  if (inflight) {
    await inflight;
    return;
  }

  const fetchTask = (async () => {
    try {
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/translation/batch`, {
        method: "POST",
        credentials: "include",
        headers: withAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          target_locale: normalized,
          source_locale: BASE_LOCALE,
          namespace: "translation",
          entries: translationEntries
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to load translations for ${normalized}: ${response.status}`);
      }

      const payload: TranslationBatchResponse = await response.json();
      const resource = expandResource(payload.translations);
      i18n.addResourceBundle(normalized, "translation", resource, true, true);
      if (typeof i18n.reloadResources === "function") {
        await i18n.reloadResources([normalized]);
      }
    } catch (error) {
      if (typeof console !== "undefined") {
        console.warn("Dynamic locale loading failed", error);
      }
    } finally {
      pendingLocaleLoads.delete(normalized);
    }
  })();

  pendingLocaleLoads.set(normalized, fetchTask);
  await fetchTask;
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
    void setAppLanguage(initialLocale);
  }
}

const resolved = normalizeLocale(i18n.resolvedLanguage ?? i18n.language ?? initialLocale) ?? BASE_LOCALE;

if (typeof document !== "undefined") {
  document.documentElement.lang = resolved;
}

persistLocale(resolved);
void ensureLocaleResources(resolved);

i18n.on("languageChanged", (language) => {
  const normalized = normalizeLocale(language) ?? BASE_LOCALE;
  if (typeof document !== "undefined") {
    document.documentElement.lang = normalized;
  }
  persistLocale(normalized);
  void ensureLocaleResources(normalized);
});

export default i18n;

export async function setAppLanguage(locale: string): Promise<void> {
  const normalized = normalizeLocale(locale) ?? BASE_LOCALE;
  await ensureLocaleResources(normalized);
  await i18n.changeLanguage(normalized);
}

function flattenResource(
  resource: Record<string, unknown>,
  prefix = ""
): TranslationFlatMap {
  const result: TranslationFlatMap = {};
  for (const [key, value] of Object.entries(resource)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      result[path] = value;
      continue;
    }

    if (value && typeof value === "object" && !Array.isArray(value)) {
      Object.assign(result, flattenResource(value as Record<string, unknown>, path));
    }
  }
  return result;
}

function expandResource(flat: TranslationFlatMap): Record<string, unknown> {
  const root: Record<string, unknown> = {};
  for (const [path, text] of Object.entries(flat)) {
    const segments = path.split(".");
    let cursor: Record<string, unknown> = root;
    segments.forEach((segment, index) => {
      if (index === segments.length - 1) {
        cursor[segment] = text;
        return;
      }
      if (typeof cursor[segment] !== "object" || cursor[segment] === null) {
        cursor[segment] = {};
      }
      cursor = cursor[segment] as Record<string, unknown>;
    });
  }
  return root;
}
