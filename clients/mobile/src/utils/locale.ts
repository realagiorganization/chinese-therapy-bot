export type CopyLocale = "zh" | "en" | "ru";

/**
 * Normalize any locale string to the app's copy buckets.
 * Defaults to Chinese when the locale is unknown.
 */
export function toCopyLocale(locale?: string | null): CopyLocale {
  const normalized = locale?.toLowerCase() ?? "";
  if (normalized.startsWith("ru")) {
    return "ru";
  }
  if (normalized.startsWith("en")) {
    return "en";
  }
  return "zh";
}
