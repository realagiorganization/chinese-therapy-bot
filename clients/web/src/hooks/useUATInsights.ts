import { useEffect, useMemo, useState } from "react";

import { loadUATInsights } from "../api/uat";
import type {
  PilotUATBacklogItem,
  PilotUATGroupSummary,
  PilotUATIssueSummary,
  PilotUATSessionSummary
} from "../api/types";
import type { LoadUATInsightsParams, UATInsightsSource } from "../api/uat";

export type NormalizedBacklogItem = PilotUATBacklogItem & {
  id: string;
  parsedLatestSessionDate: Date | null;
};

export type UATInsightsState = {
  summary: PilotUATSessionSummary | null;
  severity: PilotUATIssueSummary[];
  platforms: PilotUATGroupSummary[];
  environments: PilotUATGroupSummary[];
  backlog: NormalizedBacklogItem[];
  isLoading: boolean;
  error: Error | null;
  source: UATInsightsSource | null;
};

function parseIsoDate(value: string): Date | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function useUATInsights(params: LoadUATInsightsParams = {}): UATInsightsState {
  const [summary, setSummary] = useState<PilotUATSessionSummary | null>(null);
  const [severity, setSeverity] = useState<PilotUATIssueSummary[]>([]);
  const [platforms, setPlatforms] = useState<PilotUATGroupSummary[]>([]);
  const [environments, setEnvironments] = useState<PilotUATGroupSummary[]>([]);
  const [backlog, setBacklog] = useState<NormalizedBacklogItem[]>([]);
  const [source, setSource] = useState<UATInsightsSource | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        const payload = await loadUATInsights(params);
        if (cancelled) {
          return;
        }
        setSummary(payload.summary);
        setSeverity(payload.summary.issuesBySeverity);
        setPlatforms(payload.summary.sessionsByPlatform);
        setEnvironments(payload.summary.sessionsByEnvironment);
        setBacklog(
          payload.backlog.items.map((item, index) => ({
            ...item,
            id: `${item.title}-${index}`,
            parsedLatestSessionDate: parseIsoDate(item.latestSessionDate)
          }))
        );
        setSource(payload.source);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setSummary(null);
          setSeverity([]);
          setPlatforms([]);
          setEnvironments([]);
          setBacklog([]);
          setSource(null);
          setError(err instanceof Error ? err : new Error("Unknown UAT insights error"));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [params.cohort, params.environment]);

  const sortedSeverity = useMemo(() => {
    return [...severity].sort((a, b) => b.count - a.count);
  }, [severity]);

  const sortedBacklog = useMemo(() => {
    return [...backlog].sort((a, b) => {
      const aTime = a.parsedLatestSessionDate?.getTime() ?? 0;
      const bTime = b.parsedLatestSessionDate?.getTime() ?? 0;
      return bTime - aTime;
    });
  }, [backlog]);

  return {
    summary,
    severity: sortedSeverity,
    platforms,
    environments,
    backlog: sortedBacklog,
    isLoading,
    error,
    source
  };
}
