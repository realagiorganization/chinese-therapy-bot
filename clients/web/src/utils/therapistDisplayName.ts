import type { TFunction } from "i18next";

const NAME_NAMESPACE = "therapists.names";

function buildNameKey(id: string): string {
  if (!id) {
    return "";
  }
  return `${NAME_NAMESPACE}.${id}`;
}

export function formatTherapistDisplayName(
  id: string | null | undefined,
  nativeName: string,
  translate: TFunction<"translation">
): string {
  const fallback = (nativeName ?? "").trim();
  if (!id) {
    return fallback;
  }

  const key = buildNameKey(id);
  if (!key) {
    return fallback;
  }

  const raw = translate(key, { defaultValue: "", skipInterpolation: true });
  const localized = typeof raw === "string" ? raw.trim() : "";

  if (!localized || localized === key || localized === fallback) {
    return fallback;
  }

  return `${fallback} (${localized})`;
}

