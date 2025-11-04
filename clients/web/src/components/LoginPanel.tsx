import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  exchangeGoogleCode,
  exchangeSmsCode,
  exchangeWeChatCode,
  requestSmsChallenge
} from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Typography } from "../design-system";
import { LocaleSwitcher } from "./LocaleSwitcher";

type SmsChallengeState = {
  challengeId: string;
  expiresAt: number;
  detail: string;
};

function computeExpiry(expiresIn: number): number {
  const ttlSeconds = Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : 3600;
  return Date.now() + ttlSeconds * 1000;
}

export function LoginPanel() {
  const { t, i18n } = useTranslation();
  const { setTokens } = useAuth();

  const [phoneNumber, setPhoneNumber] = useState("");
  const [countryCode, setCountryCode] = useState("+86");
  const [otpCode, setOtpCode] = useState("");
  const [challenge, setChallenge] = useState<SmsChallengeState | null>(null);
  const [smsStatus, setSmsStatus] = useState<"idle" | "sending" | "sent" | "verifying">("idle");
  const [error, setError] = useState<string | null>(null);
  const [googleCode, setGoogleCode] = useState("");
  const [googleStatus, setGoogleStatus] = useState<"idle" | "submitting">("idle");
  const [wechatCode, setWeChatCode] = useState("");
  const [wechatStatus, setWeChatStatus] = useState<"idle" | "submitting">("idle");

  const hasActiveChallenge = useMemo(() => {
    if (!challenge) {
      return false;
    }
    return challenge.expiresAt > Date.now();
  }, [challenge]);

  const smsHint = useMemo(() => {
    if (!challenge || !hasActiveChallenge) {
      return null;
    }
    const remainingSeconds = Math.max(0, Math.round((challenge.expiresAt - Date.now()) / 1000));
    return t("auth.sms_pending", { seconds: remainingSeconds });
  }, [challenge, hasActiveChallenge, t]);

  const resolvedLocale = i18n.resolvedLanguage ?? i18n.language ?? "zh-CN";

  const handleRequestSmsCode = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      if (!phoneNumber.trim()) {
        setError(t("auth.errors.phone_required"));
        return;
      }

      setSmsStatus("sending");
      setError(null);
      try {
        const payload = await requestSmsChallenge({
          phoneNumber,
          countryCode,
          locale: resolvedLocale
        });
        const expiresAt = computeExpiry(payload.expiresIn);
        setChallenge({
          challengeId: payload.challengeId,
          expiresAt,
          detail: payload.detail
        });
        setSmsStatus("sent");
      } catch (err) {
        setSmsStatus("idle");
        setChallenge(null);
        setError(err instanceof Error ? err.message : t("auth.errors.sms_unknown"));
      }
    },
    [phoneNumber, countryCode, resolvedLocale, t]
  );

  const handleVerifySmsCode = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      if (!challenge || !hasActiveChallenge) {
        setError(t("auth.errors.challenge_missing"));
        return;
      }
      if (!otpCode.trim()) {
        setError(t("auth.errors.code_required"));
        return;
      }

      setSmsStatus("verifying");
      setError(null);
      try {
        const tokenPair = await exchangeSmsCode({
          challengeId: challenge.challengeId,
          code: otpCode
        });
        setTokens({
          accessToken: tokenPair.accessToken,
          refreshToken: tokenPair.refreshToken,
          expiresAt: computeExpiry(tokenPair.expiresIn)
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : t("auth.errors.sms_unknown"));
        setSmsStatus("sent");
      }
    },
    [challenge, hasActiveChallenge, otpCode, setTokens, t]
  );

  const handleGoogleLogin = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      if (!googleCode.trim()) {
        setError(t("auth.errors.google_code_required"));
        return;
      }
      setGoogleStatus("submitting");
      setError(null);

      try {
        const tokenPair = await exchangeGoogleCode({ code: googleCode.trim() });
        setTokens({
          accessToken: tokenPair.accessToken,
          refreshToken: tokenPair.refreshToken,
          expiresAt: computeExpiry(tokenPair.expiresIn)
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : t("auth.errors.google_unknown"));
        setGoogleStatus("idle");
      }
    },
    [googleCode, setTokens, t]
  );

  const handleWeChatLogin = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      if (!wechatCode.trim()) {
        setError(t("auth.errors.wechat_code_required"));
        return;
      }
      setWeChatStatus("submitting");
      setError(null);

      try {
        const tokenPair = await exchangeWeChatCode({ code: wechatCode.trim() });
        setTokens({
          accessToken: tokenPair.accessToken,
          refreshToken: tokenPair.refreshToken,
          expiresAt: computeExpiry(tokenPair.expiresIn)
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : t("auth.errors.wechat_unknown"));
        setWeChatStatus("idle");
      }
    },
    [wechatCode, setTokens, t]
  );

  const canRequestSms = smsStatus === "idle" || smsStatus === "sent";
  const canVerifySms = smsStatus === "sent" || smsStatus === "verifying";
  const isVerifying = smsStatus === "verifying";
  const isSendingSms = smsStatus === "sending";

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
        onSubmit={handleVerifySmsCode}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.sms_section")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.phone_label")}</span>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "100px 1fr",
              gap: "var(--mw-spacing-xs)"
            }}
          >
            <input
              type="text"
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value)}
              style={{
                padding: "10px",
                borderRadius: "var(--mw-radius-md)",
                border: "1px solid var(--mw-border-subtle)",
                fontSize: "1rem"
              }}
              placeholder="+86"
            />
            <input
              type="tel"
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              style={{
                padding: "10px",
                borderRadius: "var(--mw-radius-md)",
                border: "1px solid var(--mw-border-subtle)",
                fontSize: "1rem"
              }}
              placeholder={t("auth.phone_placeholder")}
            />
          </div>
        </label>
        <Button
          type="button"
          disabled={!canRequestSms || isSendingSms}
          onClick={(event) => {
            void handleRequestSmsCode(event);
          }}
        >
          {isSendingSms ? t("auth.sending_code") : t("auth.send_code")}
        </Button>

        {hasActiveChallenge && (
          <div
            style={{
              background: "rgba(59,130,246,0.08)",
              borderRadius: "var(--mw-radius-md)",
              padding: "var(--mw-spacing-xs)"
            }}
          >
            <Typography variant="caption" style={{ color: "var(--mw-color-primary)" }}>
              {smsHint ?? challenge?.detail}
            </Typography>
          </div>
        )}

        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.code_label")}</span>
          <input
            type="text"
            value={otpCode}
            onChange={(event) => setOtpCode(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem",
              letterSpacing: "4px",
              textAlign: "center"
            }}
            placeholder="123456"
            maxLength={6}
          />
        </label>
        <Button type="submit" disabled={!canVerifySms || isVerifying}>
          {isVerifying ? t("auth.verifying") : t("auth.verify_code")}
        </Button>
      </form>

      <form
        onSubmit={handleGoogleLogin}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.google_section")}
        </Typography>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("auth.google_hint")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.google_code_label")}</span>
          <input
            type="text"
            value={googleCode}
            onChange={(event) => setGoogleCode(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem"
            }}
            placeholder="demo-oauth-code"
          />
        </label>
        <Button type="submit" variant="secondary" disabled={googleStatus === "submitting"}>
          {googleStatus === "submitting" ? t("auth.google_submitting") : t("auth.google_cta")}
        </Button>
      </form>

      <form
        onSubmit={handleWeChatLogin}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
          {t("auth.wechat_section")}
        </Typography>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("auth.wechat_hint")}
        </Typography>
        <label style={{ display: "grid", gap: "4px", fontSize: "0.9rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>{t("auth.wechat_code_label")}</span>
          <input
            type="text"
            value={wechatCode}
            onChange={(event) => setWeChatCode(event.target.value)}
            style={{
              padding: "10px",
              borderRadius: "var(--mw-radius-md)",
              border: "1px solid var(--mw-border-subtle)",
              fontSize: "1rem"
            }}
            placeholder="wechat-miniapp-code"
          />
        </label>
        <Button type="submit" variant="ghost" disabled={wechatStatus === "submitting"}>
          {wechatStatus === "submitting" ? t("auth.wechat_submitting") : t("auth.wechat_cta")}
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
