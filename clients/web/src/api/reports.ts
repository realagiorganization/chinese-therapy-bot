import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asNumber, asRecord, asString, asStringArray } from "./parsing";
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

type JourneyFallbackCopy = {
  daily: Array<{
    title: string;
    spotlight: string;
    summary: string;
    moodDelta: number;
  }>;
  weekly: Array<{
    themes: string[];
    highlights: string;
    actionItems: string[];
    riskLevel: WeeklyJourneyReport["riskLevel"];
  }>;
  conversations: Array<{
    messages: Array<{ role: "user" | "assistant"; content: string }>;
  }>;
};

const JOURNEY_FALLBACK_TEMPLATE: JourneyFallbackCopy = {
  daily: [
    {
      title: "Today's reflection",
      spotlight: "Keep up the breathing practice and give yourself five minutes to unwind before bed.",
      summary: "Sleep quality is up compared to yesterday and anxiety keywords appeared less often.",
      moodDelta: 1
    },
    {
      title: "Yesterday's recap",
      spotlight: "Noticed stress triggers and logged two mood swings.",
      summary: "Work-related anxiety was caught early and you started documenting triggers with supportive self-talk.",
      moodDelta: 0
    },
    {
      title: "Three-day review",
      spotlight: "Completed a mindfulness exercise and recovery is speeding up.",
      summary: "Maintained a ten-minute mindful check-in and shortened recovery time from three hours to ninety minutes.",
      moodDelta: 1
    }
  ],
  weekly: [
    {
      themes: ["Stress management", "Sleep rhythm"],
      highlights: "Kept a three-night bedtime wind-down and now fall asleep about fifteen minutes faster.",
      actionItems: [
        "Write down three things you're grateful for before bed",
        "Plan one outdoor walk this weekend"
      ],
      riskLevel: "low"
    }
  ],
  conversations: [
    {
      messages: [
        {
          role: "user",
          content: "Before bed I still find my thoughts racing and my heart speeds up a little."
        },
        {
          role: "assistant",
          content:
            "Let's try a 4-7-8 breathing exercise together. Inhale for four counts, hold for seven, exhale for eight, then tell me how your body feels."
        }
      ]
    }
  ]
};

function createFallbackReports(locale: string): JourneyReportsResponse {
  const today = new Date();
  const template = JOURNEY_FALLBACK_TEMPLATE;

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

  const daily = template.daily.map((entry, index) => ({
    reportDate: isoDate(index),
    title: entry.title,
    spotlight: entry.spotlight,
    summary: entry.summary,
    moodDelta: entry.moodDelta
  })) satisfies DailyJourneyReport[];

  const weekly = template.weekly.map((entry, index) => {
    const reference = new Date(today);
    reference.setDate(reference.getDate() - index * 7);
    return {
      weekStart: startOfWeek(reference),
      themes: entry.themes,
      highlights: entry.highlights,
      actionItems: entry.actionItems,
      riskLevel: entry.riskLevel
    };
  }) satisfies WeeklyJourneyReport[];

  const conversations = template.conversations.map((conversation, index) => {
    const startedAt = new Date(today.getTime() - (index + 1) * 60 * 60 * 1000);
    const updatedAt = new Date(startedAt.getTime() + 30 * 60 * 1000);
    return {
      sessionId: `fallback-session-${index + 1}`,
      startedAt: startedAt.toISOString(),
      updatedAt: updatedAt.toISOString(),
      therapistId: null,
      messages: conversation.messages.map((message, messageIndex) => ({
        messageId: `fallback-${index + 1}-${messageIndex + 1}`,
        role: message.role,
        content: message.content,
        createdAt: new Date(startedAt.getTime() + messageIndex * 2 * 60 * 1000).toISOString()
      }))
    };
  }) satisfies JourneyConversationSlice[];

  return {
    daily,
    weekly,
    conversations
  };
}

function normalizeDailyReports(raw: unknown): DailyJourneyReport[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const reportDate = asString(data.reportDate ?? data.report_date);
    if (!reportDate) {
      return null;
    }
    return {
      reportDate,
      title: asString(data.title),
      spotlight: asString(data.spotlight),
      summary: asString(data.summary),
      moodDelta: asNumber(data.moodDelta ?? data.mood_delta)
    };
  });
}

function normalizeWeeklyReports(raw: unknown): WeeklyJourneyReport[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const weekStart = asString(data.weekStart ?? data.week_start);
    if (!weekStart) {
      return null;
    }
    const riskLevelCandidate = asString(data.riskLevel ?? data.risk_level, "low");
    const riskLevel: WeeklyJourneyReport["riskLevel"] =
      riskLevelCandidate === "high" || riskLevelCandidate === "medium" || riskLevelCandidate === "low"
        ? riskLevelCandidate
        : "low";
    return {
      weekStart,
      themes: asStringArray(data.themes),
      highlights: asString(data.highlights),
      actionItems: asStringArray(data.actionItems ?? data.action_items),
      riskLevel
    };
  });
}

function isJourneyRole(value: unknown): value is JourneyConversationMessage["role"] {
  return value === "user" || value === "assistant" || value === "system";
}

function normalizeConversationMessages(raw: unknown): JourneyConversationMessage[] {
  return asArray(raw, (message) => {
    const data = asRecord(message);
    if (!data) {
      return null;
    }
    const content = asString(data.content);
    if (!content) {
      return null;
    }
    const id =
      asString(data.messageId ?? data.message_id) ||
      (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2));
    const createdAt = asString(data.createdAt ?? data.created_at, new Date().toISOString());
    const role = isJourneyRole(data.role) ? data.role : ("assistant" as JourneyConversationMessage["role"]);
    return {
      messageId: id,
      role,
      content,
      createdAt
    };
  });
}

function normalizeConversations(raw: unknown): JourneyConversationSlice[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const sessionId = asString(data.sessionId ?? data.session_id);
    const startedAt = asString(data.startedAt ?? data.started_at);
    if (!sessionId || !startedAt) {
      return null;
    }
    const updatedAt = asString(
      data.updatedAt ?? data.updated_at ?? data.startedAt ?? data.started_at,
      startedAt
    );
    return {
      sessionId,
      startedAt,
      updatedAt,
      therapistId: data.therapistId ?? data.therapist_id ?? null,
      messages: normalizeConversationMessages(data.messages)
    };
  });
}

async function requestJourneyReports(userId: string, locale: string): Promise<JourneyReportsResponse> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (locale) {
    params.set("locale", locale);
  }
  const endpoint = `${baseUrl}/api/reports/${userId}?${params.toString()}`;
  const response = await fetch(endpoint, {
    credentials: "include",
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load journey reports (status ${response.status})`);
  }

  const data = asRecord((await response.json()) as unknown);
  if (!data) {
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
      return { ...createFallbackReports(locale), source: "fallback" };
    }
    return { ...reports, source: "api" };
  } catch (error) {
    console.warn("[JourneyReports] Falling back to illustrative payload:", error);
    return { ...createFallbackReports(locale), source: "fallback" };
  }
}
