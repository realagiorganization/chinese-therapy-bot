import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import type {
  BreathingModule,
  ExploreModule,
  PsychoeducationModule,
  TrendingTopicsModule
} from "../api/types";
import { Button, Card, Typography } from "../design-system";
import { useExploreModules } from "../hooks/useExploreModules";

type ExploreModulesProps = {
  locale: string;
};

function FlagBadge({ flagKey, enabled }: { flagKey?: string; enabled?: boolean }) {
  const { t } = useTranslation();
  if (!flagKey) {
    return null;
  }
  return (
    <span
      style={{
        fontSize: "0.75rem",
        color: enabled ? "var(--mw-color-primary)" : "var(--text-secondary)",
        background: enabled ? "rgba(59,130,246,0.12)" : "rgba(148,163,184,0.16)",
        borderRadius: "var(--mw-radius-pill)",
        padding: "2px 8px",
        fontWeight: 500
      }}
    >
      {t("explore.feature_flag_badge")}
    </span>
  );
}

function BreathingCard({
  module,
  enabled
}: {
  module: BreathingModule;
  enabled: boolean | undefined;
}) {
  const { t } = useTranslation();
  return (
    <Card
      key={module.id}
      padding="lg"
      style={{ display: "grid", gap: "var(--mw-spacing-md)", alignContent: "start" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Typography variant="subtitle">{module.title}</Typography>
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {module.description}
          </Typography>
        </div>
        <FlagBadge flagKey={module.featureFlag} enabled={enabled} />
      </div>

      <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
        {t("explore.breathing_duration", {
          minutes: module.durationMinutes,
          cadence: module.cadenceLabel
        })}
      </Typography>

      <ol style={{ margin: 0, paddingInlineStart: "1.25rem", display: "grid", gap: "6px" }}>
        {module.steps.map((step) => (
          <li key={step.label} style={{ lineHeight: 1.4 }}>
            <Typography variant="body" style={{ fontWeight: 500 }}>
              {step.label}
            </Typography>
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {step.instruction}
            </Typography>
          </li>
        ))}
      </ol>

      {module.recommendedFrequency && (
        <Typography variant="caption" style={{ color: "var(--mw-color-primary)" }}>
          {module.recommendedFrequency}
        </Typography>
      )}

      {module.ctaLabel && (
        <Button variant="secondary" style={{ justifySelf: "flex-start" }}>
          {module.ctaLabel}
        </Button>
      )}
    </Card>
  );
}

function PsychoeducationCard({
  module,
  enabled
}: {
  module: PsychoeducationModule;
  enabled: boolean | undefined;
}) {
  const { t } = useTranslation();
  return (
    <Card
      key={module.id}
      padding="lg"
      style={{ display: "grid", gap: "var(--mw-spacing-md)", alignContent: "start" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Typography variant="subtitle">{module.title}</Typography>
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {module.description}
          </Typography>
        </div>
        <FlagBadge flagKey={module.featureFlag} enabled={enabled} />
      </div>

      <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("explore.resources_heading")}
        </Typography>
        <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
          {module.resources.map((resource) => (
            <Card
              key={resource.id}
              elevated={false}
              padding="md"
              style={{
                border: "1px solid var(--mw-border-subtle)",
                background: "var(--mw-surface-subtle)"
              }}
            >
              <Typography variant="body" style={{ fontWeight: 600 }}>
                {resource.title}
              </Typography>
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {resource.summary}
              </Typography>
              <Typography variant="caption" style={{ color: "var(--text-tertiary)" }}>
                {t("explore.read_time", { minutes: resource.readTimeMinutes })}
                {" · "}
                {resource.tags.join(" / ")}
              </Typography>
            </Card>
          ))}
        </div>
      </div>

      {module.ctaLabel && (
        <Button variant="ghost" style={{ justifySelf: "flex-start" }}>
          {module.ctaLabel}
        </Button>
      )}
    </Card>
  );
}

function MomentumBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      style={{
        width: "100%",
        height: "6px",
        borderRadius: "9999px",
        background: "rgba(59,130,246,0.12)"
      }}
    >
      <div
        style={{
          width: `${clamped}%`,
          height: "100%",
          borderRadius: "9999px",
          background: "linear-gradient(90deg, #2563EB, #38BDF8)"
        }}
      />
    </div>
  );
}

function TrendingCard({
  module,
  enabled
}: {
  module: TrendingTopicsModule;
  enabled: boolean | undefined;
}) {
  const { t } = useTranslation();
  const trendLabel = (trend: "up" | "steady" | "down") => {
    switch (trend) {
      case "up":
        return t("explore.trend_up");
      case "down":
        return t("explore.trend_down");
      default:
        return t("explore.trend_steady");
    }
  };

  return (
    <Card
      key={module.id}
      padding="lg"
      style={{ display: "grid", gap: "var(--mw-spacing-md)", alignContent: "start" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Typography variant="subtitle">{module.title}</Typography>
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {module.description}
          </Typography>
        </div>
        <FlagBadge flagKey={module.featureFlag} enabled={enabled} />
      </div>

      <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
        <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
          {t("explore.topics_heading")}
        </Typography>
        <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
          {module.topics.map((topic) => (
            <div
              key={topic.name}
              style={{
                border: "1px solid var(--mw-border-subtle)",
                borderRadius: "var(--mw-radius-md)",
                padding: "var(--mw-spacing-sm)",
                display: "grid",
                gap: "6px"
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
                <Typography variant="body" style={{ fontWeight: 600 }}>
                  {topic.name}
                </Typography>
                <Typography variant="caption" style={{ color: "var(--text-tertiary)" }}>
                  {t("explore.momentum_label", { value: topic.momentum })} · {trendLabel(topic.trend)}
                </Typography>
              </div>
              <MomentumBar value={topic.momentum} />
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {topic.summary}
              </Typography>
            </div>
          ))}
        </div>
      </div>

      {module.insights.length > 0 && (
        <div style={{ display: "grid", gap: "6px" }}>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("explore.insights_heading")}
          </Typography>
          <ul style={{ margin: 0, paddingInlineStart: "1.1rem", display: "grid", gap: "4px" }}>
            {module.insights.map((insight, index) => (
              <li key={`${module.id}-insight-${index}`} style={{ lineHeight: 1.5 }}>
                <Typography variant="caption">{insight}</Typography>
              </li>
            ))}
          </ul>
        </div>
      )}

      {module.ctaLabel && (
        <Button variant="ghost" style={{ justifySelf: "flex-start" }}>
          {module.ctaLabel}
        </Button>
      )}
    </Card>
  );
}

export function ExploreModules({ locale }: ExploreModulesProps) {
  const { t } = useTranslation();
  const { modules, isLoading, source, evaluatedFlags } = useExploreModules(locale);

  const grouped = useMemo(() => {
    const data: Record<ExploreModule["moduleType"], ExploreModule | null> = {
      breathing_exercise: null,
      psychoeducation: null,
      trending_topics: null
    };
    modules.forEach((module) => {
      data[module.moduleType] = module;
    });
    return data;
  }, [modules]);

  const hasContent = modules.length > 0;

  return (
    <section style={{ display: "grid", gap: "var(--mw-spacing-md)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "var(--mw-spacing-sm)",
          flexWrap: "wrap"
        }}
      >
        <div>
          <Typography variant="subtitle">{t("explore.section_title")}</Typography>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("explore.section_description")}
          </Typography>
        </div>
        <Typography
          variant="caption"
          style={{
            color: source === "api" ? "var(--mw-color-primary)" : "var(--text-secondary)",
            background: "rgba(59,130,246,0.08)",
            borderRadius: "var(--mw-radius-pill)",
            padding: "4px 10px",
            fontWeight: 500
          }}
        >
          {source === "api" ? t("explore.source_api") : t("explore.source_fallback")}
        </Typography>
      </div>

      {isLoading && (
        <Card padding="lg" elevated={false} style={{ opacity: 0.8 }}>
          <Typography variant="body">{t("explore.loading")}</Typography>
        </Card>
      )}

      {!isLoading && !hasContent && (
        <Card padding="lg" elevated={false}>
          <Typography variant="body">{t("explore.empty_state")}</Typography>
        </Card>
      )}

      <div
        style={{
          display: "grid",
          gap: "var(--mw-spacing-md)",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))"
        }}
      >
        {grouped.breathing_exercise && (
          <BreathingCard
            module={grouped.breathing_exercise}
            enabled={evaluatedFlags[grouped.breathing_exercise.featureFlag ?? ""] ?? true}
          />
        )}
        {grouped.psychoeducation && (
          <PsychoeducationCard
            module={grouped.psychoeducation}
            enabled={evaluatedFlags[grouped.psychoeducation.featureFlag ?? ""] ?? true}
          />
        )}
        {grouped.trending_topics && (
          <TrendingCard
            module={grouped.trending_topics}
            enabled={evaluatedFlags[grouped.trending_topics.featureFlag ?? ""] ?? true}
          />
        )}
      </div>
    </section>
  );
}
