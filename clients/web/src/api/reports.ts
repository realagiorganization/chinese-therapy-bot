import { getApiBaseUrl } from "./client";
import type {
  JourneyConversationMessage,
  JourneyConversationSlice,
  JourneyReportsResponse,
  WeeklyJourneyReport,
  DailyJourneyReport
} from "./types";

export type JourneyReportsSource = "api" | "fallback";

export type JourneyReportsPayload = JourneyReportsResponse & {
  source: JourneyReportsSource;
};

const FALLBACK_REPORTS: JourneyReportsResponse = (() => {
  const today = new Date();
  const isoDate = (offsetDays: number) => {
    const date = new Date(today);
    date.setDate(date.getDate() - offsetDays);
    return date.toISOString().slice(0, 10);
  };

  const startOfWeek = (date: Date) => {
    const clone = new Date(date);
    const diff = clone.getDay() === 0 ? 6 : clone.getDay() - 1;
    clone.setDate(clone.getDate() - diff);
    return clone.toISOString().slice(0, 10);
  };

  return {
    daily: [
      {
        reportDate: isoDate(0),
        title: "今日回顾",
        spotlight: "保持呼吸练习，睡前放松 5 分钟。",
        summary: "睡眠质量评分较昨日提升，焦虑关键词提及次数下降。",
        moodDelta: 1
      },
      {
        reportDate: isoDate(1),
        title: "昨日总结",
        spotlight: "识别压力源，记录两次情绪波动。",
        summary: "工作相关的焦虑被及时捕捉，开始尝试记录触发事件与自我对话。",
        moodDelta: 0
      },
      {
        reportDate: isoDate(2),
        title: "三日回顾",
        spotlight: "完成正念练习，情绪恢复更快。",
        summary: "保持 10 分钟正念观察，焦虑恢复时间由 3 小时缩短为 90 分钟。",
        moodDelta: 1
      }
    ] satisfies DailyJourneyReport[],
    weekly: [
      {
        weekStart: startOfWeek(today),
        themes: ["压力管理", "睡眠节律"],
        highlights: "坚持睡前松弛训练三晚，入睡时间提前 15 分钟。",
        actionItems: ["睡前写下三件感谢的小事", "周末安排一次户外散步"],
        riskLevel: "low"
      }
    ] satisfies WeeklyJourneyReport[],
    conversations: [
      {
        sessionId: "fallback-session",
        startedAt: new Date(today.getTime() - 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(today.getTime() - 30 * 60 * 1000).toISOString(),
        therapistId: null,
        messages: [
          {
            messageId: "fallback-1001",
            role: "user",
            content: "最近睡觉前还是会想很多事情，心跳有点快。",
            createdAt: new Date(today.getTime() - 60 * 60 * 1000).toISOString()
          },
          {
            messageId: "fallback-1002",
            role: "assistant",
            content: "我们一起做 4-7-8 呼吸练习。吸气 4 拍，屏息 7 拍，呼气 8 拍，再告诉我身体的感觉。",
            createdAt: new Date(today.getTime() - 58 * 60 * 1000).toISOString()
          }
        ]
      }
    ] satisfies JourneyConversationSlice[]
  };
})();

function normalizeDailyReports(raw: any[] | undefined): DailyJourneyReport[] {
  if (!raw) {
    return [];
  }

  return raw
    .map((entry) => ({
      reportDate: entry.reportDate ?? entry.report_date ?? "",
      title: entry.title ?? "",
      spotlight: entry.spotlight ?? "",
      summary: entry.summary ?? "",
      moodDelta: typeof entry.moodDelta === "number" ? entry.moodDelta : entry.mood_delta ?? 0
    }))
    .filter((entry) => Boolean(entry.reportDate));
}

function normalizeWeeklyReports(raw: any[] | undefined): WeeklyJourneyReport[] {
  if (!raw) {
    return [];
  }

  return raw
    .map((entry) => ({
      weekStart: entry.weekStart ?? entry.week_start ?? "",
      themes: Array.isArray(entry.themes) ? entry.themes : [],
      highlights: entry.highlights ?? "",
      actionItems: Array.isArray(entry.actionItems)
        ? entry.actionItems
        : Array.isArray(entry.action_items)
        ? entry.action_items
        : [],
      riskLevel: entry.riskLevel ?? entry.risk_level ?? "low"
    }))
    .filter((entry) => Boolean(entry.weekStart));
}

function normalizeConversationMessages(raw: any[] | undefined): JourneyConversationMessage[] {
  if (!raw) {
    return [];
  }

  return raw
    .map((message) => ({
      messageId: message.messageId ?? message.message_id ?? crypto.randomUUID?.() ?? String(Math.random()),
      role: (message.role ?? "assistant") as JourneyConversationMessage["role"],
      content: message.content ?? "",
      createdAt: message.createdAt ?? message.created_at ?? new Date().toISOString()
    }))
    .filter((message) => Boolean(message.content));
}

function normalizeConversations(raw: any[] | undefined): JourneyConversationSlice[] {
  if (!raw) {
    return [];
  }

  return raw
    .map((entry) => ({
      sessionId: entry.sessionId ?? entry.session_id ?? "",
      startedAt: entry.startedAt ?? entry.started_at ?? "",
      updatedAt: entry.updatedAt ?? entry.updated_at ?? entry.startedAt ?? entry.started_at ?? "",
      therapistId: entry.therapistId ?? entry.therapist_id ?? null,
      messages: normalizeConversationMessages(entry.messages)
    }))
    .filter((entry) => Boolean(entry.sessionId) && Boolean(entry.startedAt));
}

async function requestJourneyReports(userId: string, locale: string): Promise<JourneyReportsResponse> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (locale) {
    params.set("locale", locale);
  }
  const endpoint = `${baseUrl}/api/reports/${userId}?${params.toString()}`;
  const response = await fetch(endpoint, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to load journey reports (status ${response.status})`);
  }

  const data = await response.json();
  if (!data || typeof data !== "object") {
    throw new Error("Journey reports response is empty.");
  }

  return {
    daily: normalizeDailyReports(data.daily),
    weekly: normalizeWeeklyReports(data.weekly),
    conversations: normalizeConversations(data.conversations)
  };
}

export async function loadJourneyReports(userId: string, locale: string): Promise<JourneyReportsPayload> {
  try {
    const reports = await requestJourneyReports(userId, locale);
    const hasData =
      reports.daily.length > 0 || reports.weekly.length > 0 || reports.conversations.length > 0;
    if (!hasData) {
      return { ...FALLBACK_REPORTS, source: "fallback" };
    }
    return { ...reports, source: "api" };
  } catch (error) {
    console.warn("[JourneyReports] Falling back to illustrative payload:", error);
    return { ...FALLBACK_REPORTS, source: "fallback" };
  }
}
