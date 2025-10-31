import { useTranslation } from "react-i18next";

import { Button, Card, Typography } from "./design-system";
import { LocaleSwitcher } from "./components/LocaleSwitcher";
import { useTherapistDirectory } from "./hooks/useTherapistDirectory";

type HighlightCard = {
  id: string;
  title: string;
  summary: string;
  action: string;
};

export default function App() {
  const { t } = useTranslation();
  const {
    filtered,
    filters,
    setFilters,
    resetFilters,
    specialties,
    languages,
    isLoading,
    source,
    maxPrice
  } = useTherapistDirectory();

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

        <section style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
          <Typography variant="subtitle">{t("app.therapist_recommendations")}</Typography>
          <Card padding="md" style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.title")}
            </Typography>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "var(--mw-spacing-md)"
              }}
            >
              <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
                <span style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.filters.specialty")}
                </span>
                <select
                  value={filters.specialty ?? ""}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      specialty: event.target.value || undefined
                    }))
                  }
                  style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--mw-border-subtle)" }}
                >
                  <option value="">{t("therapists.filters.any")}</option>
                  {specialties.map((specialty) => (
                    <option key={specialty} value={specialty}>
                      {specialty}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
                <span style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.filters.language")}
                </span>
                <select
                  value={filters.language ?? ""}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      language: event.target.value || undefined
                    }))
                  }
                  style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--mw-border-subtle)" }}
                >
                  <option value="">{t("therapists.filters.any")}</option>
                  {languages.map((language) => (
                    <option key={language} value={language}>
                      {language}
                    </option>
                  ))}
                </select>
              </label>
              {maxPrice && (
                <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>
                    {t("therapists.filters.max_price", { currency: "CNY" })}
                  </span>
                  <input
                    type="number"
                    min={0}
                    max={maxPrice}
                    value={filters.maxPrice ?? ""}
                    placeholder={`${t("therapists.filters.up_to")} ${maxPrice}`}
                    onChange={(event) =>
                      setFilters((prev) => ({
                        ...prev,
                        maxPrice: event.target.value ? Number.parseInt(event.target.value, 10) : undefined
                      }))
                    }
                    style={{
                      padding: "6px 10px",
                      borderRadius: "8px",
                      border: "1px solid var(--mw-border-subtle)"
                    }}
                  />
                </label>
              )}
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)"
                }}
              >
                <input
                  type="checkbox"
                  checked={Boolean(filters.recommendedOnly)}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      recommendedOnly: event.target.checked
                    }))
                  }
                />
                {t("therapists.filters.recommended_only")}
              </label>
              <Button variant="ghost" onClick={resetFilters}>
                {t("therapists.filters.reset")}
              </Button>
            </div>
            <Typography variant="caption" style={{ color: "rgba(71,85,105,0.7)" }}>
              {source === "api"
                ? t("therapists.filters.source_api")
                : t("therapists.filters.source_fallback")}
            </Typography>
          </Card>
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-md)",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))"
            }}
          >
            {isLoading ? (
              <Card padding="lg" elevated>
                <Typography variant="body">{t("therapists.filters.loading")}</Typography>
              </Card>
            ) : filtered.length === 0 ? (
              <Card padding="lg" elevated>
                <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.filters.empty_state")}
                </Typography>
              </Card>
            ) : (
              filtered.map((therapist) => (
                <Card key={therapist.id} padding="lg" elevated>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "var(--mw-spacing-sm)"
                    }}
                  >
                    <Typography variant="title" as="h3">
                      {therapist.name}
                    </Typography>
                    {therapist.recommended && (
                      <span
                        style={{
                          background: "rgba(59,130,246,0.12)",
                          color: "var(--mw-color-primary)",
                          borderRadius: "var(--mw-radius-pill)",
                          padding: "2px 10px",
                          fontSize: "0.75rem",
                          fontWeight: 600
                        }}
                      >
                        {t("therapists.recommended")}
                      </span>
                    )}
                  </div>
                  <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                    {[therapist.title, therapist.specialties.join(" · ")].filter(Boolean).join(" ｜ ")}
                  </Typography>
                  <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                    {t("therapists.languages", { languages: therapist.languages.join(" / ") })}
                  </Typography>
                  <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                    {t("therapists.price", { price: therapist.price })}
                  </Typography>
                  {therapist.availability.length > 0 && (
                    <div
                      style={{
                        marginTop: "var(--mw-spacing-sm)",
                        display: "flex",
                        gap: "var(--mw-spacing-xs)",
                        flexWrap: "wrap"
                      }}
                    >
                      {therapist.availability.map((slot) => (
                        <span
                          key={slot}
                          style={{
                            border: "1px solid var(--mw-border-subtle)",
                            borderRadius: "var(--mw-radius-pill)",
                            padding: "4px 10px",
                            fontSize: "0.75rem",
                            color: "var(--text-secondary)"
                          }}
                        >
                          {slot}
                        </span>
                      ))}
                    </div>
                  )}
                  <Button block style={{ marginTop: "var(--mw-spacing-md)" }}>
                    {t("therapists.book")}
                  </Button>
                </Card>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
