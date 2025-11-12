import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { AuthError, exchangeOAuthSession, loginWithDemoCode } from "../api/auth";
import { getAuthProxyUrl } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Typography } from "../design-system";
import { LocaleSwitcher } from "./LocaleSwitcher";

const OAUTH_PENDING_KEY = "mindwell:oauth:pending";

type EmailStatus = "idle" | "checking" | "redirecting";
type DemoStatus = "idle" | "submitting";

function setPendingOAuth(status: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (status) {
      window.localStorage.setItem(OAUTH_PENDING_KEY, "1");
    } else {
      window.localStorage.removeItem(OAUTH_PENDING_KEY);
    }
  } catch {
    // ignore storage failures
  }
}

function isPendingOAuth(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    return window.localStorage.getItem(OAUTH_PENDING_KEY) === "1";
  } catch {
    return false;
  }
}

function hasProxySessionCookie(): boolean {
  if (typeof document === "undefined") {
    return false;
  }
  try {
    return document.cookie
      .split(";")
      .some((entry) => entry.trim().startsWith("_oauth2_proxy="));
  } catch {
    return false;
  }
}

export function LoginPanel() {
  const { t } = useTranslation();
  const { setTokens } = useAuth();

  const [email, setEmail] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [emailStatus, setEmailStatus] = useState<EmailStatus>("idle");
  const [demoStatus, setDemoStatus] = useState<DemoStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const skipOAuthRef = useRef(false);

  const isCheckingOAuth = emailStatus === "checking";
  const isRedirecting = emailStatus === "redirecting";

  useEffect(() => {
    let cancelled = false;
    const pending = isPendingOAuth();
    if (!pending || !hasProxySessionCookie()) {
      if (pending) {
        setPendingOAuth(false);
      }
      return () => {
        cancelled = true;
      };
    }

    setEmailStatus("checking");

    (async () => {
      try {
        const tokens = await exchangeOAuthSession();
        if (cancelled || skipOAuthRef.current) {
          return;
        }
        if (!cancelled) {
          setTokens({
            accessToken: tokens.accessToken,
            refreshToken: tokens.refreshToken,
            expiresAt: Date.now() + tokens.expiresIn * 1000
          });
          setError(null);
        }
      } catch (err) {
        if (cancelled || skipOAuthRef.current) {
          return;
        }
        if (err instanceof AuthError && err.status === 401) {
          setError(null);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(t("auth.errors.oauth_unknown"));
        }
      } finally {
        if (!cancelled) {
          setEmailStatus("idle");
          setPendingOAuth(false);
        }
      }
    })().catch(() => {
      if (!cancelled) {
        setEmailStatus("idle");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [setTokens, t]);

  const handleEmailSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      skipOAuthRef.current = false;
      const form = event.currentTarget;
      const formData = new FormData(form);
      const emailEntry = formData.get("email");
      const emailElement = form.elements.namedItem("email") as HTMLInputElement | null;
      const rawEmail =
        typeof emailEntry === "string"
          ? emailEntry
          : emailElement?.value !== undefined
            ? emailElement.value
            : "";
      const trimmed = rawEmail.trim();
      if (!trimmed) {
        setError(t("auth.errors.email_required"));
        return;
      }
      setError(null);
      setEmail(trimmed);
      setPendingOAuth(true);
      setEmailStatus("redirecting");

      if (typeof window !== "undefined") {
        const base = window.location.origin;
        const redirectTarget = `${base}${window.location.pathname}`;
        const search = new URLSearchParams();
        search.set("rd", redirectTarget);
        search.set("prompt", "select_account");
        if (trimmed) {
          search.set("login_hint", trimmed);
          const domain = trimmed.split("@")[1]?.toLowerCase();
          if (domain) {
            search.set("hd", domain);
          }
        }
        const oauthStartUrl = `${getAuthProxyUrl("/oauth2/start")}?${search.toString()}`;
        window.location.assign(oauthStartUrl);
      }
    },
    [email, t]
  );

  const handleDemoLogin = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const form = event.currentTarget;
      const formData = new FormData(form);
      const codeEntry = formData.get("demo_code");
      const codeElement = form.elements.namedItem("demo_code") as HTMLInputElement | null;
      const rawCode =
        typeof codeEntry === "string"
          ? codeEntry
          : codeElement?.value !== undefined
            ? codeElement.value
            : "";
      const trimmed = rawCode.trim();
      if (!trimmed) {
        setError(t("auth.errors.demo_required"));
        return;
      }
      skipOAuthRef.current = true;
      setPendingOAuth(false);
      setEmailStatus("idle");
      setDemoStatus("submitting");
      setError(null);

      try {
        const tokens = await loginWithDemoCode({
          code: trimmed
        });
        setTokens({
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          expiresAt: Date.now() + tokens.expiresIn * 1000
        });
        setDemoStatus("idle");
        setDemoCode(trimmed);
      } catch (err) {
        setDemoStatus("idle");
        if (err instanceof AuthError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(t("auth.errors.demo_unknown"));
        }
      }
    },
    [demoCode, setTokens, t]
  );

  const emailButtonLabel = useMemo(() => {
    if (isRedirecting) {
      return t("auth.email_redirect");
    }
    if (isCheckingOAuth) {
      return t("auth.email_checking");
    }
    return t("auth.email_cta");
  }, [isRedirecting, isCheckingOAuth, t]);

  return (
    <Card
      elevated
      padding="lg"
      style={{
        maxWidth: "420px",
        width: "100%",
        display: "grid",
        gap: "var(--mw-spacing-lg)",
        background: "linear-gradient(0deg, rgba(226,232,240,0.5) 0%, rgba(255,255,255,0.92) 80%)"
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
          <Typography variant="title">{t("auth.title")}</Typography>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("auth.subtitle")}
          </Typography>
        </div>
        <LocaleSwitcher compact />
      </div>

      <form
        onSubmit={handleEmailSubmit}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.email_section")}
        </Typography>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("auth.email_hint")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.email_label")}</span>
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
            placeholder={t("auth.email_placeholder")}
            autoComplete="email"
          />
        </label>

        <Button type="submit" disabled={isRedirecting || isCheckingOAuth}>
          {emailButtonLabel}
        </Button>
      </form>

      <form
        onSubmit={handleDemoLogin}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.demo_section")}
        </Typography>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("auth.demo_hint")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.demo_label")}</span>
          <input
            type="text"
            name="demo_code"
            value={demoCode}
            onChange={(event) => setDemoCode(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem",
              letterSpacing: "2px"
            }}
            placeholder={t("auth.demo_placeholder")}
          />
        </label>
        <Button type="submit" variant="secondary" disabled={demoStatus === "submitting"}>
          {demoStatus === "submitting" ? t("auth.demo_submitting") : t("auth.demo_cta")}
        </Button>
      </form>

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
