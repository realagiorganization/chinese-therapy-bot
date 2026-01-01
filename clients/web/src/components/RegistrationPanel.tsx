import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { AuthError, registerWithEmail } from "../api/auth";
import { trackAnalyticsEvent } from "../api/analytics";
import { getAuthProxyUrl } from "../api/client";
import { isPendingOAuth, setPendingOAuth, triggerOAuthRedirect } from "../auth/oauthState";
import { Button, Card, Typography } from "../design-system";
import { LocaleSwitcher } from "./LocaleSwitcher";

type AuthViewHandler = () => void;

type RegistrationStatus = "idle" | "submitting" | "redirecting";

type RegistrationPanelProps = {
  onShowLogin?: AuthViewHandler;
};

function isValidEmail(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
}

export function RegistrationPanel({ onShowLogin }: RegistrationPanelProps) {
  const { t, i18n } = useTranslation();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [status, setStatus] = useState<RegistrationStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const isSubmitting = status === "submitting";
  const isRedirecting = status === "redirecting";

  const pendingOAuth = useMemo(() => isPendingOAuth(), []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (isRedirecting || isSubmitting) {
        return;
      }

      const trimmedName = fullName.trim();
      const trimmedEmail = email.trim();

      if (!trimmedName) {
        setError(t("auth.registration.errors.name_required"));
        return;
      }
      if (!isValidEmail(trimmedEmail)) {
        setError(t("auth.registration.errors.email_invalid"));
        return;
      }
      if (!acceptTerms) {
        setError(t("auth.registration.errors.terms_required"));
        return;
      }

      setError(null);
      setStatus("submitting");

      await trackAnalyticsEvent({
        eventType: "signup_started",
        funnelStage: "activation",
        properties: {
          source: "registration_form"
        }
      });

      try {
        const response = await registerWithEmail({
          email: trimmedEmail,
          displayName: trimmedName,
          locale: i18n.language,
          acceptTerms
        });

        if (response.status === "existing") {
          setStatus("idle");
          setError(t("auth.registration.errors.already_registered"));
          return;
        }

        setPendingOAuth(true);
        setStatus("redirecting");

        if (typeof window === "undefined") {
          setStatus("idle");
          setPendingOAuth(false);
          return;
        }

        const redirectTarget = window.location.href;
        const search = new URLSearchParams();
        search.set("rd", redirectTarget);
        search.set("prompt", "select_account");
        search.set("login_hint", trimmedEmail);
        const domain = trimmedEmail.split("@")[1]?.toLowerCase();
        if (domain) {
          search.set("hd", domain);
        }
        const oauthStartUrl = `${getAuthProxyUrl("/oauth2/start")}?${search.toString()}`;
        triggerOAuthRedirect(oauthStartUrl);
      } catch (err) {
        setStatus("idle");
        if (err instanceof AuthError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(t("auth.registration.errors.unknown"));
        }
      }
    },
    [acceptTerms, email, fullName, i18n.language, isRedirecting, isSubmitting, t]
  );

  return (
    <Card
      elevated
      padding="lg"
      style={{
        maxWidth: "440px",
        width: "100%",
        display: "grid",
        gap: "var(--mw-spacing-lg)",
        background: "linear-gradient(0deg, rgba(226,232,240,0.55) 0%, rgba(255,255,255,0.96) 84%)"
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "var(--mw-spacing-sm)",
          flexWrap: "wrap"
        }}
      >
        <div style={{ display: "grid", gap: "var(--mw-spacing-xs)" }}>
          <Typography variant="title">{t("auth.registration.title")}</Typography>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("auth.registration.subtitle")}
          </Typography>
        </div>
        <LocaleSwitcher compact />
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.registration.section")}
        </Typography>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {pendingOAuth ? t("auth.registration.oauth_pending") : t("auth.registration.hint")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {t("auth.registration.name_label")}
          </span>
          <input
            type="text"
            name="full_name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem"
            }}
            placeholder={t("auth.registration.name_placeholder")}
            autoComplete="name"
          />
        </label>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {t("auth.registration.email_label")}
          </span>
          <input
            type="email"
            name="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem"
            }}
            placeholder={t("auth.registration.email_placeholder")}
            autoComplete="email"
          />
        </label>

        <label
          style={{
            display: "flex",
            gap: "8px",
            alignItems: "flex-start",
            fontSize: "0.88rem",
            color: "var(--text-secondary)"
          }}
        >
          <input
            type="checkbox"
            checked={acceptTerms}
            onChange={(event) => setAcceptTerms(event.target.checked)}
            style={{ marginTop: "3px" }}
          />
          <span>{t("auth.registration.terms_label")}</span>
        </label>

        <Button type="submit" disabled={isSubmitting || isRedirecting}>
          {isRedirecting
            ? t("auth.registration.redirecting")
            : isSubmitting
              ? t("auth.registration.submitting")
              : t("auth.registration.cta")}
        </Button>
      </form>

      {onShowLogin && (
        <div style={{ display: "grid", gap: "6px" }}>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("auth.registration.have_account")}
          </Typography>
          <Button type="button" variant="ghost" onClick={onShowLogin}>
            {t("auth.registration.login_cta")}
          </Button>
        </div>
      )}

      {error && (
        <div
          style={{
            background: "rgba(248,113,113,0.12)",
            borderRadius: "var(--mw-radius-md)",
            padding: "var(--mw-spacing-xs)"
          }}
        >
          <Typography variant="caption" style={{ color: "var(--mw-color-danger)" }}>
            {error}
          </Typography>
        </div>
      )}
    </Card>
  );
}
