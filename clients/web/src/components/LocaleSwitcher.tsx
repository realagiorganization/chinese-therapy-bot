import { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import { Typography } from "../design-system";

const supportedLocales = [
  { code: "zh", labelKey: "locale.zh" },
  { code: "en", labelKey: "locale.en" }
];

type LocaleSwitcherProps = {
  compact?: boolean;
};

export function LocaleSwitcher({ compact = false }: LocaleSwitcherProps) {
  const { i18n, t } = useTranslation();

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    i18n.changeLanguage(event.target.value);
    document.documentElement.lang = event.target.value;
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
        value={i18n.language.startsWith("zh") ? "zh" : "en"}
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
