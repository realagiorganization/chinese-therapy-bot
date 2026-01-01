import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "./auth/AuthContext";
import { isPendingOAuth } from "./auth/oauthState";
import { Button, Card, Typography } from "./design-system";
import { ChatPanel } from "./components/ChatPanel";
import { ExploreModules } from "./components/ExploreModules";
import { LoginPanel } from "./components/LoginPanel";
import { JourneyDashboard } from "./components/JourneyDashboard";
import { LocaleSwitcher } from "./components/LocaleSwitcher";
import { RegistrationPanel } from "./components/RegistrationPanel";
import { TherapistDirectory } from "./components/TherapistDirectory";

type HighlightCard = {
  id: string;
  title: string;
  summary: string;
  action: string;
};

export default function App() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated, clearTokens } = useAuth();
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const pendingOAuth = useMemo(() => isPendingOAuth(), []);
  const gradientBackground =
    "linear-gradient(0deg, var(--mw-gradient-bottom) 0%, var(--mw-gradient-mid) 38%, var(--mw-gradient-top) 80%)";

  const highlightCards: HighlightCard[] = [
    {
      id: "today",
      title: t("app.daily_reflection"),
      summary: t("app.daily_reflection_summary"),
      action: t("app.cta_resume")
    },
    {
      id: "insight",
      title: t("journey.insight_spotlight"),
      summary: t("app.insight_summary"),
      action: t("journey.next_steps")
    }
  ];

  if (!isAuthenticated) {
    const showLogin = pendingOAuth || authView === "login";
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: "clamp(24px, 4vw, 64px)",
          background: gradientBackground
        }}
      >
        {showLogin ? (
          <LoginPanel onShowRegistration={() => setAuthView("register")} />
        ) : (
          <RegistrationPanel onShowLogin={() => setAuthView("login")} />
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "clamp(24px, 4vw, 64px)",
        background: gradientBackground
      }}
    >
      <div
        style={{
          display: "grid",
          gap: "var(--mw-spacing-lg)",
          maxWidth: "1080px",
          margin: "0 auto"
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "var(--mw-spacing-md)"
          }}
        >
          <Typography variant="title">{t("app.title")}</Typography>
          <div
            style={{
              display: "flex",
              gap: "var(--mw-spacing-xs)",
              alignItems: "center"
            }}
          >
            <LocaleSwitcher />
            <Button variant="ghost" size="sm" onClick={clearTokens}>
              {t("auth.logout")}
            </Button>
          </div>
        </header>

        <Card
          elevated
          padding="lg"
          style={{
            display: "grid",
            gap: "var(--mw-spacing-md)",
            background:
              "linear-gradient(135deg, var(--mw-color-accent-blue-green) 0%, rgba(255,255,255,0.92) 65%, rgba(255,255,255,0.98) 100%)",
            color: "#0F172A",
            border: "1px solid rgba(255,255,255,0.6)"
          }}
        >
          <Typography variant="overline" style={{ color: "rgba(15,23,42,0.72)" }}>
            {t("journey.streak", { days: 7 })}
          </Typography>
          <Typography variant="display" style={{ color: "#0F172A" }}>
            {t("app.welcome", { name: "Aurora" })}
          </Typography>
          <Typography variant="subtitle" style={{ color: "rgba(15,23,42,0.72)" }}>
            {t("app.tagline")}
          </Typography>
          <Typography variant="caption" style={{ color: "rgba(15,23,42,0.72)" }}>
            {t("app.voice_hint")}
          </Typography>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "var(--mw-spacing-sm)"
            }}
          >
            <Button size="lg">{t("app.cta_start")}</Button>
            <Button variant="secondary" size="lg">
              {t("app.cta_resume")}
            </Button>
            <Button variant="ghost" size="lg">
              {t("app.cta_invite")}
            </Button>
          </div>
        </Card>

        <ChatPanel />

        <JourneyDashboard locale={i18n.language} />
        <ExploreModules locale={i18n.language} />

        <section
          style={{
            display: "grid",
            gap: "var(--mw-spacing-md)",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))"
          }}
        >
          {highlightCards.map((card) => (
            <Card key={card.id} elevated padding="lg">
              <Typography variant="subtitle">{card.title}</Typography>
              <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                {card.summary}
              </Typography>
              <Button variant="ghost" style={{ paddingLeft: 0 }}>
                {card.action}
              </Button>
            </Card>
          ))}
        </section>

        <TherapistDirectory />
      </div>
    </div>
  );
}
