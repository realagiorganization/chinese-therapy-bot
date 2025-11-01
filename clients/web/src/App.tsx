import { useTranslation } from "react-i18next";

import { Button, Card, Typography } from "./design-system";
import { ChatPanel } from "./components/ChatPanel";
import { JourneyDashboard } from "./components/JourneyDashboard";
import { LocaleSwitcher } from "./components/LocaleSwitcher";
import { TherapistDirectory } from "./components/TherapistDirectory";

type HighlightCard = {
  id: string;
  title: string;
  summary: string;
  action: string;
};

export default function App() {
  const { t, i18n } = useTranslation();

  const highlightCards: HighlightCard[] = [
    {
      id: "today",
      title: t("app.daily_reflection"),
      summary: "继续记录你的情绪触发点，今晚尝试 5 分钟呼吸放松。",
      action: t("app.cta_resume")
    },
    {
      id: "insight",
      title: t("journey.insight_spotlight"),
      summary: "近 3 天焦虑关键词出现频率下降 18%。",
      action: t("journey.next_steps")
    }
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "clamp(24px, 4vw, 64px)",
        background: "linear-gradient(180deg, rgba(59,130,246,0.08) 0%, rgba(248,250,252,1) 40%)"
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
          <LocaleSwitcher />
        </header>

        <Card
          elevated
          padding="lg"
          style={{
            display: "grid",
            gap: "var(--mw-spacing-md)",
            background:
              "linear-gradient(135deg, rgba(37,99,235,0.92) 0%, rgba(59,130,246,0.78) 60%, rgba(255,255,255,0.98) 100%)",
            color: "#0F172A"
          }}
        >
          <Typography variant="overline" style={{ color: "rgba(15,23,42,0.72)" }}>
            {t("journey.streak", { days: 7 })}
          </Typography>
          <Typography variant="display" style={{ color: "#0F172A" }}>
            {t("app.welcome", { name: "晨曦" })}
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
