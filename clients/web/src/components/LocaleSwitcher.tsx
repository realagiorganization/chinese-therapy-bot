import { useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import { Typography } from "../design-system";
import { setAppLanguage } from "../i18n/config";

const supportedLocales = [
  { code: "zh-CN", labelKey: "locale.zh_cn" },
  { code: "zh-TW", labelKey: "locale.zh_tw" },
  { code: "en-US", labelKey: "locale.en_us" },
  { code: "ru-RU", labelKey: "locale.ru_ru" }
] as const;

type LocaleSwitcherProps = {
  compact?: boolean;
};

export function LocaleSwitcher({ compact = false }: LocaleSwitcherProps) {
  const { i18n, t } = useTranslation();
  const [pendingLocale, setPendingLocale] = useState<string | null>(null);

  const resolveLocale = (code: string | undefined): string => {
    if (!code) {
      return supportedLocales[0].code;
    }
    const match = supportedLocales.find((locale) => locale.code.toLowerCase() === code.toLowerCase());
    return match ? match.code : supportedLocales[0].code;
  };

  const currentLocale = resolveLocale(pendingLocale ?? i18n.language ?? i18n.resolvedLanguage);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = resolveLocale(event.target.value);
    setPendingLocale(nextLocale);
    void setAppLanguage(nextLocale).finally(() => {
      setPendingLocale(null);
    });
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "var(--mw-spacing-sm)",
        alignItems: "center"
      }}
    >
      {!compact && (
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("app.language_label")}
        </Typography>
      )}
      <select
        value={currentLocale}
        onChange={handleChange}
        style={{
          minHeight: "38px",
          borderRadius: "var(--mw-radius-md)",
          border: "1px solid var(--mw-border-subtle)",
          padding: "0 var(--mw-spacing-sm)",
          background: "var(--mw-surface-card)",
          color: "var(--text-primary)",
          fontFamily: "var(--mw-font-base)",
          fontWeight: "var(--mw-font-weight-medium)"
        }}
      >
        {supportedLocales.map((locale) => (
          <option key={locale.code} value={locale.code}>
            {t(locale.labelKey)}
          </option>
        ))}
      </select>
    </div>
  );
}
