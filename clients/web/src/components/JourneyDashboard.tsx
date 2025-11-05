import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Card, Typography, Button } from "../design-system";
import { useJourneyReports } from "../hooks/useJourneyReports";

type JourneyDashboardProps = {
  locale: string;
};

type DetailTab = "summary" | "transcript";

function resolveLocale(locale: string): string {
  const normalized = (locale ?? "").toLowerCase();
  if (normalized.startsWith("zh-tw") || normalized.startsWith("zh_hant")) {
    return "zh-TW";
  }
  if (normalized.startsWith("zh")) {
    return "zh-CN";
  }
  if (normalized.startsWith("ru")) {
    return "ru-RU";
  }
  if (normalized.startsWith("en")) {
    return "en-US";
  }
  return "zh-CN";
}

export function JourneyDashboard({ locale }: JourneyDashboardProps) {
  const resolvedLocale = resolveLocale(locale);
  const { t } = useTranslation();
  const { daily, weekly, conversationsByDate, isLoading, source } = useJourneyReports(resolvedLocale);

  const [selectedDailyId, setSelectedDailyId] = useState<string | null>(null);
  const [tab, setTab] = useState<DetailTab>("summary");

  useEffect(() => {
    if (daily.length > 0) {
      setSelectedDailyId(daily[0].id);
    }
  }, [daily]);

  useEffect(() => {
    setTab("summary");
  }, [selectedDailyId]);

  const selectedDaily = useMemo(
    () => daily.find((report) => report.id === selectedDailyId) ?? null,
    [daily, selectedDailyId]
  );

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(resolvedLocale, {
        month: "short",
        day: "numeric",
        weekday: resolvedLocale === "zh-CN" ? "short" : "short"
      }),
    [resolvedLocale]
  );

  const longDateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(resolvedLocale, {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long"
      }),
    [resolvedLocale]
  );

  const moodLabel = useMemo(() => {
    if (!selectedDaily) {
      return "";
    }
    if (selectedDaily.moodDelta > 0) {
      return t("journey.mood_up", { value: selectedDaily.moodDelta });
    }
    if (selectedDaily.moodDelta < 0) {
      return t("journey.mood_down", { value: Math.abs(selectedDaily.moodDelta) });
    }
    return t("journey.mood_flat");
  }, [selectedDaily, t]);

  const conversationsForSelected = useMemo(() => {
    if (!selectedDaily) {
      return [];
    }
    return conversationsByDate.get(selectedDaily.reportDate) ?? [];
  }, [conversationsByDate, selectedDaily]);

  return (
    <section style={{ display: "grid", gap: "var(--mw-spacing-md)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <Typography variant="subtitle">{t("journey.section_title")}</Typography>
        {source === "fallback" && (
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("journey.fallback_notice")}
          </Typography>
        )}
      </div>
      <Card padding="lg" style={{ display: "grid", gap: "var(--mw-spacing-md)" }}>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("journey.daily_reports")}
        </Typography>
        {isLoading ? (
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {t("journey.loading")}
          </Typography>
        ) : daily.length === 0 ? (
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {t("journey.empty")}
          </Typography>
        ) : (
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-sm)",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))"
            }}
          >
            {daily.map((report) => {
              const isActive = report.id === selectedDailyId;
              return (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => setSelectedDailyId(report.id)}
                  style={{
                    border: isActive ? "1px solid var(--mw-color-primary)" : "1px solid var(--mw-border-subtle)",
                    borderRadius: "var(--mw-radius-md)",
                    background: isActive ? "rgba(37,99,235,0.08)" : "var(--mw-surface-card)",
                    padding: "var(--mw-spacing-md)",
                    textAlign: "left",
                    cursor: "pointer",
                    boxShadow: isActive ? "var(--mw-shadow-md)" : "none"
                  }}
                >
                  <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
                    {report.parsedDate ? dateFormatter.format(report.parsedDate) : report.reportDate}
                  </Typography>
                  <Typography variant="body" style={{ marginTop: "4px" }}>
                    {report.title}
                  </Typography>
                  <Typography variant="caption" style={{ color: "var(--text-secondary)", marginTop: "4px" }}>
                    {report.spotlight}
                  </Typography>
                  <Typography variant="caption" style={{ color: "var(--mw-color-primary)", marginTop: "6px" }}>
                    {report.moodDelta === 0
                      ? t("journey.mood_flat")
                      : t(report.moodDelta > 0 ? "journey.mood_up" : "journey.mood_down", {
                          value: Math.abs(report.moodDelta)
                        })}
                  </Typography>
                </button>
              );
            })}
          </div>
        )}

        {selectedDaily && (
          <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "var(--mw-spacing-sm)",
                alignItems: "center"
              }}
            >
              <Typography variant="title">
                {selectedDaily.parsedDate
                  ? longDateFormatter.format(selectedDaily.parsedDate)
                  : selectedDaily.reportDate}
              </Typography>
              <span
                style={{
                  background: "rgba(37,99,235,0.12)",
                  color: "var(--mw-color-primary)",
                  borderRadius: "var(--mw-radius-pill)",
                  padding: "4px 12px",
                  fontSize: "0.8rem"
                }}
              >
                {moodLabel}
              </span>
            </div>
            <div
              role="tablist"
              style={{
                display: "flex",
                gap: "var(--mw-spacing-xs)",
                background: "var(--mw-surface-muted)",
                borderRadius: "var(--mw-radius-pill)",
                padding: "4px"
              }}
            >
              <button
                type="button"
                role="tab"
                aria-selected={tab === "summary"}
                onClick={() => setTab("summary")}
                style={{
                  flex: 1,
                  border: "none",
                  borderRadius: "var(--mw-radius-pill)",
                  background: tab === "summary" ? "var(--mw-surface-card)" : "transparent",
                  padding: "8px 12px",
                  cursor: "pointer",
                  fontWeight: tab === "summary" ? 600 : 500
                }}
              >
                {t("journey.tab_summary")}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={tab === "transcript"}
                onClick={() => setTab("transcript")}
                style={{
                  flex: 1,
                  border: "none",
                  borderRadius: "var(--mw-radius-pill)",
                  background: tab === "transcript" ? "var(--mw-surface-card)" : "transparent",
                  padding: "8px 12px",
                  cursor: "pointer",
                  fontWeight: tab === "transcript" ? 600 : 500
                }}
              >
                {t("journey.tab_conversation")}
              </button>
            </div>

            {tab === "summary" ? (
              <Card elevated={false} padding="md" style={{ background: "var(--mw-surface-card)" }}>
                <Typography variant="subtitle">{selectedDaily.title}</Typography>
                <Typography variant="body" style={{ marginTop: "var(--mw-spacing-sm)" }}>
                  {selectedDaily.summary}
                </Typography>
                <Typography variant="caption" style={{ color: "var(--text-secondary)", marginTop: "var(--mw-spacing-sm)" }}>
                  {selectedDaily.spotlight}
                </Typography>
              </Card>
            ) : conversationsForSelected.length === 0 ? (
              <Card elevated={false} padding="md">
                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {t("journey.conversation_empty")}
                </Typography>
              </Card>
            ) : (
              conversationsForSelected.map((conversation) => (
                <Card key={conversation.sessionId} elevated={false} padding="md">
                  <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                    {t("journey.conversation_started", {
                      timestamp: conversation.parsedStartedAt
                        ? new Intl.DateTimeFormat(resolvedLocale, {
                            hour: "2-digit",
                            minute: "2-digit"
                          }).format(conversation.parsedStartedAt)
                        : conversation.startedAt
                    })}
                  </Typography>
                  <div
                    style={{
                      display: "grid",
                      gap: "var(--mw-spacing-xs)",
                      marginTop: "var(--mw-spacing-sm)"
                    }}
                  >
                    {conversation.messages.map((message) => (
                      <div
                        key={message.messageId}
                        style={{
                          display: "grid",
                          gap: "4px",
                          background:
                            message.role === "assistant" ? "rgba(59,130,246,0.08)" : "rgba(15,23,42,0.04)",
                          borderRadius: "var(--mw-radius-md)",
                          padding: "10px 12px"
                        }}
                      >
                        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                          {message.role === "assistant" ? t("journey.role_assistant") : t("journey.role_user")}
                        </Typography>
                        <Typography variant="body">{message.content}</Typography>
                      </div>
                    ))}
                  </div>
                </Card>
              ))
            )}
          </div>
        )}
      </Card>

      {weekly.length > 0 && (
        <Card padding="lg" style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("journey.weekly_reports")}
          </Typography>
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-sm)",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))"
            }}
          >
            {weekly.map((report) => (
              <Card key={report.id} elevated={false} padding="md" style={{ border: "1px solid var(--mw-border-subtle)" }}>
                <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
                  {report.parsedWeekStart
                    ? dateFormatter.format(report.parsedWeekStart)
                    : report.weekStart}
                </Typography>
                <Typography variant="body" style={{ marginTop: "4px" }}>
                  {t("journey.themes")}
                </Typography>
                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {report.themes.join(" · ")}
                </Typography>
                <Typography variant="body" style={{ marginTop: "var(--mw-spacing-sm)" }}>
                  {report.highlights}
                </Typography>
                {report.actionItems.length > 0 && (
                  <div style={{ marginTop: "var(--mw-spacing-sm)", display: "grid", gap: "4px" }}>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {t("journey.action_items")}
                    </Typography>
                    <ul style={{ margin: 0, paddingLeft: "20px", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                      {report.actionItems.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <Typography variant="caption" style={{ color: "var(--text-secondary)", marginTop: "var(--mw-spacing-sm)" }}>
                  {t("journey.risk_level", { level: report.riskLevel })}
                </Typography>
              </Card>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--mw-spacing-sm)" }}>
        <Button variant="ghost">{t("journey.export_pdf")}</Button>
        <Button variant="ghost">{t("journey.share_with_therapist")}</Button>
      </div>
    </section>
  );
}
