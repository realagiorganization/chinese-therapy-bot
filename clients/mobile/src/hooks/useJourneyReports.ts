import { useAuth } from "@context/AuthContext";
import { useCallback, useEffect, useMemo, useState } from "react";

import { loadJourneyReports } from "../services/reports";
import type {
  DailyJourneyReport,
  JourneyConversationSlice,
  JourneyReportsSource,
  WeeklyJourneyReport,
} from "../types/journey";

export type NormalizedDailyReport = DailyJourneyReport & {
  id: string;
  parsedDate: Date | null;
};

export type NormalizedWeeklyReport = WeeklyJourneyReport & {
  id: string;
  parsedWeekStart: Date | null;
};

export type NormalizedConversationSlice = JourneyConversationSlice & {
  parsedStartedAt: Date | null;
  parsedUpdatedAt: Date | null;
};

export type JourneyReportsState = {
  daily: NormalizedDailyReport[];
  weekly: NormalizedWeeklyReport[];
  conversations: NormalizedConversationSlice[];
  conversationsByDate: Map<string, NormalizedConversationSlice[]>;
  isLoading: boolean;
  error: Error | null;
  source: JourneyReportsSource | null;
  refresh: () => Promise<void>;
};

function parseDate(value: string | undefined): Date | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function computeDailyId(report: DailyJourneyReport): string {
  return report.reportDate;
}

function computeWeeklyId(report: WeeklyJourneyReport): string {
  return report.weekStart;
}

function computeConversationKey(
  conversation: NormalizedConversationSlice,
): string {
  if (conversation.parsedStartedAt) {
    return conversation.parsedStartedAt.toISOString().slice(0, 10);
  }
  return conversation.startedAt.slice(0, 10);
}

export function useJourneyReports(locale: string): JourneyReportsState {
  const { userId, tokens } = useAuth();
  const accessToken = tokens?.accessToken ?? null;
  const [daily, setDaily] = useState<DailyJourneyReport[]>([]);
  const [weekly, setWeekly] = useState<WeeklyJourneyReport[]>([]);
  const [conversations, setConversations] = useState<
    JourneyConversationSlice[]
  >([]);
  const [source, setSource] = useState<JourneyReportsSource | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    try {
      const { reports, source: reportsSource } = await loadJourneyReports({
        userId,
        locale,
        accessToken,
      });
      setDaily(reports.daily);
      setWeekly(reports.weekly);
      setConversations(reports.conversations);
      setSource(reportsSource);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Journey load failed"));
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, locale, userId]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setIsLoading(true);
      try {
        const { reports, source: reportsSource } = await loadJourneyReports({
          userId,
          locale,
          accessToken,
        });
        if (!cancelled) {
          setDaily(reports.daily);
          setWeekly(reports.weekly);
          setConversations(reports.conversations);
          setSource(reportsSource);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Journey load failed"),
          );
          setSource("fallback");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [accessToken, locale, userId]);

  const normalized = useMemo(() => {
    const normalizedDaily: NormalizedDailyReport[] = daily.map((report) => ({
      ...report,
      id: computeDailyId(report),
      parsedDate: parseDate(report.reportDate),
    }));

    const normalizedWeekly: NormalizedWeeklyReport[] = weekly.map((report) => ({
      ...report,
      id: computeWeeklyId(report),
      parsedWeekStart: parseDate(report.weekStart),
    }));

    const normalizedConversations: NormalizedConversationSlice[] =
      conversations.map((conversation) => ({
        ...conversation,
        parsedStartedAt: parseDate(conversation.startedAt),
        parsedUpdatedAt: parseDate(conversation.updatedAt),
      }));

    const mapByDate = new Map<string, NormalizedConversationSlice[]>();
    normalizedConversations.forEach((conversation) => {
      const key = computeConversationKey(conversation);
      if (!mapByDate.has(key)) {
        mapByDate.set(key, []);
      }
      mapByDate.get(key)?.push(conversation);
    });

    return {
      normalizedDaily,
      normalizedWeekly,
      normalizedConversations,
      mapByDate,
    };
  }, [conversations, daily, weekly]);

  const refresh = useCallback(async () => {
    await fetchReports();
  }, [fetchReports]);

  return {
    daily: normalized.normalizedDaily,
    weekly: normalized.normalizedWeekly,
    conversations: normalized.normalizedConversations,
    conversationsByDate: normalized.mapByDate,
    isLoading,
    error,
    source,
    refresh,
  };
}
