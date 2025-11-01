import { apiRequest } from "./api/client";
import type {
  DailyJourneyReport,
  JourneyConversationMessage,
  JourneyConversationSlice,
  JourneyReportsResponse,
  JourneyReportsSource,
  WeeklyJourneyReport,
} from "../types/journey";

type ApiJourneyReportsResponse = {
  daily?: unknown[];
  weekly?: unknown[];
  conversations?: unknown[];
};

type LoadJourneyReportsParams = {
  userId: string | null;
  locale: string;
  accessToken?: string | null;
};

const FALLBACK_REPORTS: JourneyReportsResponse = (() => {
  const today = new Date();
  const toIsoDate = (offset: number) => {
    const date = new Date(today);
    date.setDate(date.getDate() - offset);
    return date.toISOString().slice(0, 10);
  };

  const startOfWeek = (date: Date) => {
    const clone = new Date(date);
    const day = clone.getDay();
    const diff = day === 0 ? 6 : day - 1;
    clone.setDate(clone.getDate() - diff);
    return clone.toISOString().slice(0, 10);
  };

  return {
    daily: Array.from({ length: 5 }, (_, index) => ({
      reportDate: toIsoDate(index),
      title: index === 0 ? "今日亮点" : "每日回顾",
      spotlight:
        index === 0
          ? "保持 4-7-8 呼吸练习，临睡前身体更放松。"
          : "继续记录情绪波动，识别触发时刻。",
      summary:
        index === 0
          ? "对焦虑的提及次数下降，睡眠入睡时间提前 10 分钟。"
          : "维持情绪记忆日志，日均两次快速自我检查，焦虑恢复在 90 分钟内。",
      moodDelta: index === 0 ? 1 : 0,
    })),
    weekly: [
      {
        weekStart: startOfWeek(today),
        themes: ["压力管理", "睡眠节律"],
        highlights: "完成三晚睡前松弛练习，夜间醒来次数减少。",
        actionItems: ["继续呼吸练习", "安排一次户外散步", "与朋友交流支持"],
        riskLevel: "low",
      },
    ],
    conversations: [
      {
        sessionId: "fallback-session",
        startedAt: new Date(today.getTime() - 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(today.getTime() - 35 * 60 * 1000).toISOString(),
        therapistId: null,
        messages: [
          {
            messageId: "fallback-1",
            role: "user",
            content: "最近入睡前还是会紧张，心跳有点快。",
            createdAt: new Date(today.getTime() - 60 * 60 * 1000).toISOString(),
          },
          {
            messageId: "fallback-2",
            role: "assistant",
            content: "我们试试 4-7-8 呼吸法，吸气 4 拍，屏息 7 拍，呼气 8 拍。",
            createdAt: new Date(today.getTime() - 58 * 60 * 1000).toISOString(),
          },
        ],
      },
    ],
  };
})();

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function toString(value: unknown): string | undefined {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return undefined;
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => (typeof entry === "string" ? entry : null))
    .filter((entry): entry is string => Boolean(entry));
}

function normalizeDailyReports(raw: unknown[]): DailyJourneyReport[] {
  return raw
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) {
        return null;
      }
      const reportDate = toString(record.reportDate ?? record.report_date);
      if (!reportDate) {
        return null;
      }
      return {
        reportDate,
        title: toString(record.title) ?? "每日总结",
        spotlight: toString(record.spotlight) ?? "",
        summary: toString(record.summary) ?? "",
        moodDelta: toNumber(record.moodDelta ?? record.mood_delta) ?? 0,
      };
    })
    .filter((value): value is DailyJourneyReport => Boolean(value));
}

function normalizeWeeklyReports(raw: unknown[]): WeeklyJourneyReport[] {
  return raw
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) {
        return null;
      }
      const weekStart = toString(record.weekStart ?? record.week_start);
      if (!weekStart) {
        return null;
      }
      const riskLevelCandidate =
        toString(record.riskLevel ?? record.risk_level) ?? "low";
      const riskLevel =
        riskLevelCandidate === "high" ||
        riskLevelCandidate === "medium" ||
        riskLevelCandidate === "low"
          ? riskLevelCandidate
          : "low";
      return {
        weekStart,
        themes: toStringArray(record.themes),
        highlights: toString(record.highlights) ?? "",
        actionItems: toStringArray(record.actionItems ?? record.action_items),
        riskLevel,
      };
    })
    .filter((value): value is WeeklyJourneyReport => Boolean(value));
}

function normalizeMessages(raw: unknown): JourneyConversationMessage[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) {
        return null;
      }
      const content = toString(record.content);
      if (!content) {
        return null;
      }
      const roleCandidate = toString(record.role);
      const role =
        roleCandidate === "user" ||
        roleCandidate === "assistant" ||
        roleCandidate === "system"
          ? roleCandidate
          : "assistant";
      return {
        messageId:
          toString(record.messageId ?? record.message_id) ??
          Math.random().toString(36).slice(2),
        role,
        content,
        createdAt:
          toString(record.createdAt ?? record.created_at) ??
          new Date().toISOString(),
      };
    })
    .filter((value): value is JourneyConversationMessage => Boolean(value));
}

function normalizeConversations(raw: unknown[]): JourneyConversationSlice[] {
  return raw
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) {
        return null;
      }
      const sessionId = toString(record.sessionId ?? record.session_id);
      const startedAt = toString(record.startedAt ?? record.started_at);
      if (!sessionId || !startedAt) {
        return null;
      }
      const updatedAt =
        toString(record.updatedAt ?? record.updated_at) ?? startedAt;
      return {
        sessionId,
        startedAt,
        updatedAt,
        therapistId:
          toString(record.therapistId ?? record.therapist_id) ?? null,
        messages: normalizeMessages(record.messages ?? []),
      };
    })
    .filter((value): value is JourneyConversationSlice => Boolean(value));
}

function mapJourneyReports(
  payload: ApiJourneyReportsResponse,
): JourneyReportsResponse {
  const daily = normalizeDailyReports(
    Array.isArray(payload.daily) ? payload.daily : [],
  );
  const weekly = normalizeWeeklyReports(
    Array.isArray(payload.weekly) ? payload.weekly : [],
  );
  const conversations = normalizeConversations(
    Array.isArray(payload.conversations) ? payload.conversations : [],
  );
  return { daily, weekly, conversations };
}

export async function loadJourneyReports({
  userId,
  locale,
  accessToken,
}: LoadJourneyReportsParams): Promise<{
  reports: JourneyReportsResponse;
  source: JourneyReportsSource;
}> {
  if (!userId) {
    return { reports: FALLBACK_REPORTS, source: "fallback" };
  }

  const params = new URLSearchParams();
  if (locale) {
    params.set("locale", locale);
  }

  try {
    const payload = await apiRequest<ApiJourneyReportsResponse>(
      `/reports/${encodeURIComponent(userId)}?${params.toString()}`,
      {
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      },
    );
    const reports = mapJourneyReports(payload);
    if (
      reports.daily.length === 0 &&
      reports.weekly.length === 0 &&
      reports.conversations.length === 0
    ) {
      return { reports: FALLBACK_REPORTS, source: "fallback" };
    }
    return { reports, source: "api" };
  } catch (error) {
    console.warn("[Journey] Falling back to seed data:", error);
    return { reports: FALLBACK_REPORTS, source: "fallback" };
  }
}
