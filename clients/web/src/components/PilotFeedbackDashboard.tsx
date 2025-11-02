import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Button, Card, Typography } from "../design-system";
import { usePilotFeedback } from "../hooks/usePilotFeedback";

type PilotFeedbackDashboardProps = {
  cohort?: string;
  limit?: number;
};

function formatDate(value: string | null, locale: string, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

export function PilotFeedbackDashboard({
  cohort = "pilot-2025w4",
  limit = 6
}: PilotFeedbackDashboardProps) {
  const { t, i18n } = useTranslation();
  const { backlog, participants, recentFeedback, source, isLoading, error, refresh } =
    usePilotFeedback({ cohort, limit });

  const locale = i18n.language;
  const emptyStateLabel = t("pilot.empty_backlog");

  const formattedBacklog = useMemo(
    () =>
      backlog.map((item) => ({
        ...item,
        formattedSubmittedAt: formatDate(item.lastSubmittedAt, locale, "-"),
        sentimentLabel: t("pilot.sentiment_label", {
          value: item.averageSentiment.toFixed(1)
        }),
        trustLabel: t("pilot.trust_label", {
          value: item.averageTrust.toFixed(1)
        }),
        usabilityLabel: t("pilot.usability_label", {
          value: item.averageUsability.toFixed(1)
        }),
        priorityLabel: t("pilot.priority_label", {
          value: item.priorityScore.toFixed(2)
        }),
        frequencyLabel: t("pilot.frequency_label", { value: item.frequency }),
        followUpLabel: t("pilot.followups_label", { value: item.followUpCount })
      })),
    [backlog, locale, t]
  );

  const formattedParticipants = useMemo(
    () =>
      participants.map((participant) => ({
        ...participant,
        statusLabel: t("pilot.participant_status", { status: participant.status }),
        lastContactLabel: participant.lastContactAt
          ? formatDate(participant.lastContactAt, locale, t("pilot.never_contacted"))
          : t("pilot.never_contacted"),
        cohortLabel: t("pilot.cohort_label", { cohort: participant.cohort }),
        channelLabel: t("pilot.channel_label", { channel: participant.channel }),
        tagsLabel:
          participant.tags.length > 0
            ? t("pilot.tags", { tags: participant.tags.join(", ") })
            : null
      })),
    [participants, locale, t]
  );

  const formattedFeedback = useMemo(
    () =>
      recentFeedback.map((entry) => ({
        ...entry,
        submittedLabel: formatDate(entry.submittedAt, locale, "-"),
        followUpLabel: entry.followUpNeeded
          ? t("pilot.follow_up_required")
          : t("pilot.follow_up_not_required"),
        scenarioLabel: entry.scenario
          ? t("pilot.scenario_label", { scenario: entry.scenario })
          : null,
        tagsLabel:
          entry.tags.length > 0 ? t("pilot.tags", { tags: entry.tags.join(", ") }) : null
      })),
    [recentFeedback, locale, t]
  );

  return (
    <section>
      <Card
        elevated
        padding="lg"
        style={{
          display: "grid",
          gap: "var(--mw-spacing-md)"
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "var(--mw-spacing-sm)"
          }}
        >
          <div>
            <Typography variant="subtitle">{t("pilot.section_title")}</Typography>
            <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
              {t("pilot.section_description")}
            </Typography>
          </div>
          <Button variant="secondary" size="sm" disabled={isLoading} onClick={refresh}>
            {t("pilot.refresh")}
          </Button>
        </header>

        {source === "fallback" && (
          <Typography variant="caption" style={{ color: "var(--mw-color-warning)" }}>
            {t("pilot.source_fallback")}
          </Typography>
        )}

        {error && source !== "fallback" && (
          <Typography variant="caption" style={{ color: "var(--mw-color-danger)" }}>
            {t("pilot.load_error")}
          </Typography>
        )}

        {isLoading ? (
          <Typography variant="body" style={{ color: "var(--mw-text-secondary)" }}>
            {t("pilot.loading")}
          </Typography>
        ) : (
          <div
            style={{
              display: "grid",
              gap: "var(--mw-spacing-lg)"
            }}
          >
            <section
              style={{
                display: "grid",
                gap: "var(--mw-spacing-sm)"
              }}
            >
              <Typography variant="overline" style={{ color: "var(--mw-text-secondary)" }}>
                {t("pilot.backlog_heading")}
              </Typography>
              {formattedBacklog.length === 0 ? (
                <Typography variant="body" style={{ color: "var(--mw-text-secondary)" }}>
                  {emptyStateLabel}
                </Typography>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: "var(--mw-spacing-sm)",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))"
                  }}
                >
                  {formattedBacklog.map((item) => (
                    <div
                      key={`${item.label}-${item.tag ?? "untagged"}`}
                      style={{
                        border: "1px solid var(--mw-border-subtle)",
                        borderRadius: "var(--mw-radius-md)",
                        padding: "var(--mw-spacing-md)",
                        background: "var(--mw-surface-card)",
                        display: "grid",
                        gap: "var(--mw-spacing-xs)"
                      }}
                    >
                      <Typography variant="body" style={{ fontWeight: 600 }}>
                        {item.label}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {item.priorityLabel} · {item.frequencyLabel} · {item.followUpLabel}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {item.sentimentLabel} · {item.trustLabel} · {item.usabilityLabel}
                      </Typography>
                      {item.scenario ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {t("pilot.scenario_label", { scenario: item.scenario })}
                        </Typography>
                      ) : null}
                      {item.tag ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {t("pilot.tag_label", { tag: item.tag })}
                        </Typography>
                      ) : null}
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {t("pilot.submitted", { value: item.formattedSubmittedAt })}
                      </Typography>
                      <div
                        style={{
                          display: "grid",
                          gap: "4px",
                          marginTop: "var(--mw-spacing-xs)"
                        }}
                      >
                        <Typography variant="caption" style={{ fontWeight: 600 }}>
                          {t("pilot.backlog_highlights")}
                        </Typography>
                        {item.highlights.length === 0 ? (
                          <Typography
                            variant="caption"
                            style={{ color: "var(--mw-text-secondary)" }}
                          >
                            {t("pilot.no_highlights")}
                          </Typography>
                        ) : (
                          item.highlights.map((highlight, index) => (
                            <Typography
                              key={`${item.label}-highlight-${index}`}
                              variant="caption"
                              style={{ color: "var(--mw-text-secondary)" }}
                            >
                              • {highlight}
                            </Typography>
                          ))
                        )}
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gap: "4px"
                        }}
                      >
                        <Typography variant="caption" style={{ fontWeight: 600 }}>
                          {t("pilot.backlog_blockers")}
                        </Typography>
                        {item.blockers.length === 0 ? (
                          <Typography
                            variant="caption"
                            style={{ color: "var(--mw-text-secondary)" }}
                          >
                            {t("pilot.no_blockers")}
                          </Typography>
                        ) : (
                          item.blockers.map((blocker, index) => (
                            <Typography
                              key={`${item.label}-blocker-${index}`}
                              variant="caption"
                              style={{ color: "var(--mw-text-secondary)" }}
                            >
                              • {blocker}
                            </Typography>
                          ))
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section
              style={{
                display: "grid",
                gap: "var(--mw-spacing-sm)"
              }}
            >
              <Typography variant="overline" style={{ color: "var(--mw-text-secondary)" }}>
                {t("pilot.participants_heading")}
              </Typography>
              {formattedParticipants.length === 0 ? (
                <Typography variant="body" style={{ color: "var(--mw-text-secondary)" }}>
                  {t("pilot.empty_participants")}
                </Typography>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: "var(--mw-spacing-sm)",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))"
                  }}
                >
                  {formattedParticipants.map((participant) => (
                    <div
                      key={participant.id}
                      style={{
                        border: "1px solid var(--mw-border-subtle)",
                        borderRadius: "var(--mw-radius-md)",
                        padding: "var(--mw-spacing-md)",
                        background: "var(--mw-surface-card)",
                        display: "grid",
                        gap: "var(--mw-spacing-xs)"
                      }}
                    >
                      <Typography variant="body" style={{ fontWeight: 600 }}>
                        {participant.displayName}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {participant.statusLabel}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {participant.cohortLabel} · {participant.channelLabel}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {t("pilot.last_contact", { value: participant.lastContactLabel })}
                      </Typography>
                      {participant.tagsLabel ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {participant.tagsLabel}
                        </Typography>
                      ) : null}
                      {participant.followUpNotes ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {participant.followUpNotes}
                        </Typography>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section
              style={{
                display: "grid",
                gap: "var(--mw-spacing-sm)"
              }}
            >
              <Typography variant="overline" style={{ color: "var(--mw-text-secondary)" }}>
                {t("pilot.feedback_heading")}
              </Typography>
              {formattedFeedback.length === 0 ? (
                <Typography variant="body" style={{ color: "var(--mw-text-secondary)" }}>
                  {t("pilot.empty_feedback")}
                </Typography>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: "var(--mw-spacing-sm)"
                  }}
                >
                  {formattedFeedback.map((entry) => (
                    <div
                      key={entry.id}
                      style={{
                        border: "1px solid var(--mw-border-subtle)",
                        borderRadius: "var(--mw-radius-md)",
                        padding: "var(--mw-spacing-md)",
                        background: "var(--mw-surface-card)",
                        display: "grid",
                        gap: "var(--mw-spacing-xs)"
                      }}
                    >
                      <Typography variant="body" style={{ fontWeight: 600 }}>
                        {entry.participantAlias ?? entry.id}
                      </Typography>
                      <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                        {entry.followUpLabel} ·{" "}
                        {t("pilot.submitted", { value: entry.submittedLabel })}
                      </Typography>
                      {entry.scenarioLabel ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {entry.scenarioLabel}
                        </Typography>
                      ) : null}
                      {entry.tagsLabel ? (
                        <Typography
                          variant="caption"
                          style={{ color: "var(--mw-text-secondary)" }}
                        >
                          {entry.tagsLabel}
                        </Typography>
                      ) : null}
                      {entry.highlights ? (
                        <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                          {entry.highlights}
                        </Typography>
                      ) : (
                        <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                          {t("pilot.no_highlights")}
                        </Typography>
                      )}
                      {entry.blockers ? (
                        <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                          {entry.blockers}
                        </Typography>
                      ) : (
                        <Typography variant="caption" style={{ color: "var(--mw-text-secondary)" }}>
                          {t("pilot.no_blockers")}
                        </Typography>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </Card>
    </section>
  );
}
