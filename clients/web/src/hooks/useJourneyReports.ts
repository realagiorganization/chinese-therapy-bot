import { useEffect, useMemo, useState } from "react";

import { loadJourneyReports } from "../api/reports";
import type {
  DailyJourneyReport,
  JourneyConversationSlice,
  JourneyReportsResponse,
  WeeklyJourneyReport
} from "../api/types";
import type { JourneyReportsSource } from "../api/reports";
import { useAuth } from "../auth/AuthContext";

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
  source: JourneyReportsSource | null;
  error: Error | null;
};

function parseDate(value: string | undefined): Date | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function useJourneyReports(locale: string): JourneyReportsState {
  const [reports, setReports] = useState<JourneyReportsResponse | null>(null);
  const [source, setSource] = useState<JourneyReportsSource | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { userId } = useAuth();

  useEffect(() => {
    if (!userId) {
      setReports(null);
      setSource(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        const payload = await loadJourneyReports(userId, locale);
        if (!cancelled) {
          setReports({
            daily: payload.daily,
            weekly: payload.weekly,
            conversations: payload.conversations
          });
          setSource(payload.source);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setReports(null);
          setSource("fallback");
          setError(err instanceof Error ? err : new Error("Unknown journey reports error"));
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
  }, [locale, userId]);

  const normalized = useMemo(() => {
    if (!reports) {
      return {
        daily: [] as NormalizedDailyReport[],
        weekly: [] as NormalizedWeeklyReport[],
        conversations: [] as NormalizedConversationSlice[],
        conversationsByDate: new Map<string, NormalizedConversationSlice[]>()
      };
    }

    const daily = reports.daily.map((report) => ({
      ...report,
      id: report.reportDate,
      parsedDate: parseDate(report.reportDate)
    }));

    const weekly = reports.weekly.map((report) => ({
      ...report,
      id: report.weekStart,
      parsedWeekStart: parseDate(report.weekStart)
    }));

    const conversations = reports.conversations.map((conversation) => ({
      ...conversation,
      parsedStartedAt: parseDate(conversation.startedAt),
      parsedUpdatedAt: parseDate(conversation.updatedAt)
    }));

    const conversationsByDate = new Map<string, NormalizedConversationSlice[]>();
    conversations.forEach((conversation) => {
      const key =
        conversation.parsedStartedAt?.toISOString().slice(0, 10) ??
        conversation.startedAt.slice(0, 10);
      if (!conversationsByDate.has(key)) {
        conversationsByDate.set(key, []);
      }
      conversationsByDate.get(key)?.push(conversation);
    });

    return {
      daily,
      weekly,
      conversations,
      conversationsByDate
    };
  }, [reports]);

  return {
    daily: normalized.daily,
    weekly: normalized.weekly,
    conversations: normalized.conversations,
    conversationsByDate: normalized.conversationsByDate,
    isLoading,
    source,
    error
  };
}
