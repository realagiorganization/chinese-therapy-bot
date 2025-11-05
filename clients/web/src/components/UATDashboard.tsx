import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Card, Typography } from "../design-system";
import { useUATInsights } from "../hooks/useUATInsights";

type UATDashboardProps = {
  cohort?: string;
};

function formatNumber(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return value.toFixed(fractionDigits);
}

function formatDate(
  value: Date | null,
  language: string,
  fallback: string = "—"
): string {
  if (!value) {
    return fallback;
  }
  try {
    return new Intl.DateTimeFormat(language, {
      year: "numeric",
      month: "short",
      day: "numeric"
    }).format(value);
  } catch {
    return value.toISOString().slice(0, 10);
  }
}

const severityOrder = ["high", "medium", "low", "unspecified"];

export function UATDashboard({ cohort }: UATDashboardProps) {
  const { t, i18n } = useTranslation();
  const { summary, severity, platforms, environments, backlog, isLoading, error, source } =
    useUATInsights({ cohort });

  const stats = useMemo(() => {
    if (!summary) {
      return [];
    }
    return [
      {
        id: "totalSessions",
        label: t("uat.stats.totalSessions"),
        value: summary.totalSessions
      },
      {
        id: "participants",
        label: t("uat.stats.distinctParticipants"),
        value: summary.distinctParticipants
      },
      {
        id: "avgSatisfaction",
        label: t("uat.stats.averageSatisfaction"),
        value: formatNumber(summary.averageSatisfaction, 2)
      },
      {
        id: "avgTrust",
        label: t("uat.stats.averageTrust"),
        value: formatNumber(summary.averageTrust, 2)
      },
      {
        id: "blockers",
        label: t("uat.stats.sessionsWithBlockers"),
        value: summary.sessionsWithBlockers
      }
    ];
  }, [summary, t]);

  const severityItems = useMemo(() => {
    return [...severity].sort((a, b) => {
      const aIndex = severityOrder.indexOf(a.severity);
      const bIndex = severityOrder.indexOf(b.severity);
      if (aIndex === bIndex) {
        return b.count - a.count;
      }
      if (aIndex === -1 && bIndex === -1) {
        return b.count - a.count;
      }
      if (aIndex === -1) {
        return 1;
      }
      if (bIndex === -1) {
        return -1;
      }
      return aIndex - bIndex;
    });
  }, [severity]);

  const sourceLabel =
    source === "fallback" ? t("uat.source.fallback") : t("uat.source.api");

  return (
    <section
      aria-label={t("uat.title")}
      style={{
        display: "grid",
        gap: "var(--mw-spacing-lg)"
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: "var(--mw-spacing-md)"
        }}
      >
        <div>
          <Typography variant="title">{t("uat.title")}</Typography>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {sourceLabel}
          </Typography>
        </div>
        {cohort ? (
          <Typography variant="overline" style={{ textTransform: "uppercase" }}>
            {t("uat.cohortLabel", { cohort })}
          </Typography>
        ) : null}
      </div>

      {isLoading ? (
        <Card padding="lg">
          <Typography variant="body">{t("uat.state.loading")}</Typography>
        </Card>
      ) : null}

      {!isLoading && error && !summary ? (
        <Card padding="lg">
          <Typography variant="body" style={{ color: "var(--status-danger)" }}>
            {t("uat.state.error")}
          </Typography>
        </Card>
      ) : null}

      {summary ? (
        <Card padding="lg" elevated>
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-lg)",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))"
            }}
          >
            {stats.map((stat) => (
              <div key={stat.id}>
                <Typography variant="overline" style={{ color: "var(--text-secondary)" }}>
                  {stat.label}
                </Typography>
                <Typography
                  variant="title"
                  style={{ fontSize: "1.5rem", fontWeight: "var(--mw-font-weight-semibold)" }}
                >
                  {stat.value}
                </Typography>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {severityItems.length > 0 ? (
        <Card padding="lg">
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-md)"
            }}
          >
            <Typography variant="subtitle">{t("uat.sections.severity")}</Typography>
            <div
              style={{
                display: "grid",
                gap: "var(--mw-spacing-sm)",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))"
              }}
            >
              {severityItems.map((item) => (
                <div
                  key={item.severity}
                  style={{
                    padding: "var(--mw-spacing-sm)",
                    borderRadius: "12px",
                    backgroundColor: "rgba(15, 23, 42, 0.04)"
                  }}
                >
                  <Typography variant="overline" style={{ textTransform: "uppercase" }}>
                    {t(`uat.severity.${item.severity}`, item.severity)}
                  </Typography>
                  <Typography
                    variant="title"
                    style={{ fontSize: "1.5rem", fontWeight: "var(--mw-font-weight-semibold)" }}
                  >
                    {item.count}
                  </Typography>
                </div>
              ))}
            </div>
          </div>
        </Card>
      ) : null}

      {(platforms.length > 0 || environments.length > 0) && (
        <div
          style={{
            display: "grid",
            gap: "var(--mw-spacing-lg)",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))"
          }}
        >
          {platforms.length > 0 ? (
            <Card padding="lg">
              <Typography variant="subtitle">{t("uat.sections.platforms")}</Typography>
              <div
                style={{
                  display: "grid",
                  gap: "var(--mw-spacing-sm)",
                  marginTop: "var(--mw-spacing-md)"
                }}
              >
                {platforms.map((platform) => (
                  <div key={platform.key}>
                    <Typography
                      variant="body"
                      style={{ fontWeight: "var(--mw-font-weight-medium)" }}
                    >
                      {platform.key}
                    </Typography>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {t("uat.platformSummary", {
                        total: platform.total,
                        satisfaction: formatNumber(platform.averageSatisfaction, 2),
                        trust: formatNumber(platform.averageTrust, 2)
                      })}
                    </Typography>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}
          {environments.length > 0 ? (
            <Card padding="lg">
              <Typography variant="subtitle">{t("uat.sections.environments")}</Typography>
              <div
                style={{
                  display: "grid",
                  gap: "var(--mw-spacing-sm)",
                  marginTop: "var(--mw-spacing-md)"
                }}
              >
                {environments.map((environment) => (
                  <div key={environment.key}>
                    <Typography
                      variant="body"
                      style={{ fontWeight: "var(--mw-font-weight-medium)" }}
                    >
                      {environment.key}
                    </Typography>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {t("uat.environmentSummary", {
                        total: environment.total,
                        satisfaction: formatNumber(environment.averageSatisfaction, 2),
                        trust: formatNumber(environment.averageTrust, 2)
                      })}
                    </Typography>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}
        </div>
      )}

      {backlog.length > 0 ? (
        <Card padding="lg">
          <Typography variant="subtitle">{t("uat.sections.backlog")}</Typography>
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-md)",
              marginTop: "var(--mw-spacing-md)"
            }}
          >
            {backlog.map((item) => (
              <div
                key={item.id}
                style={{
                  border: "1px solid rgba(15,23,42,0.08)",
                  borderRadius: "12px",
                  padding: "var(--mw-spacing-md)"
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    gap: "var(--mw-spacing-sm)"
                  }}
                >
                  <Typography
                    variant="body"
                    style={{ fontWeight: "var(--mw-font-weight-medium)" }}
                  >
                    {item.title}
                  </Typography>
                  <Typography variant="caption" style={{ textTransform: "uppercase" }}>
                    {t(`uat.severity.${item.severity}`, item.severity)}
                  </Typography>
                </div>
                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {t("uat.backlog.meta", {
                    occurrences: item.occurrences,
                    participants: item.affectedParticipants,
                    date: formatDate(item.parsedLatestSessionDate, i18n.language)
                  })}
                </Typography>
                {item.sampleNotes.length > 0 ? (
                  <Typography variant="body" style={{ marginTop: "var(--mw-spacing-sm)" }}>
                    {item.sampleNotes[0]}
                  </Typography>
                ) : null}
                {item.actionItems.length > 0 ? (
                  <Typography variant="caption" style={{ marginTop: "var(--mw-spacing-sm)" }}>
                    {t("uat.backlog.actions", { actions: item.actionItems.join("，") })}
                  </Typography>
                ) : null}
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </section>
  );
}
