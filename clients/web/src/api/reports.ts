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

const FALLBACK_LOCALES = ["zh-CN", "zh-TW", "en-US", "ru-RU"] as const;
type FallbackLocale = (typeof FALLBACK_LOCALES)[number];

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

const JOURNEY_FALLBACK_COPY: Record<FallbackLocale, JourneyFallbackCopy> = {
  "zh-CN": {
    daily: [
      {
        title: "今日回顾",
        spotlight: "保持呼吸练习，睡前放松 5 分钟。",
        summary: "睡眠质量评分较昨日提升，焦虑关键词提及次数下降。",
        moodDelta: 1
      },
      {
        title: "昨日总结",
        spotlight: "识别压力源，记录两次情绪波动。",
        summary: "工作相关的焦虑被及时捕捉，开始尝试记录触发事件与自我对话。",
        moodDelta: 0
      },
      {
        title: "三日回顾",
        spotlight: "完成正念练习，情绪恢复更快。",
        summary: "保持 10 分钟正念观察，焦虑恢复时间由 3 小时缩短为 90 分钟。",
        moodDelta: 1
      }
    ],
    weekly: [
      {
        themes: ["压力管理", "睡眠节律"],
        highlights: "坚持睡前松弛训练三晚，入睡时间提前 15 分钟。",
        actionItems: ["睡前写下三件感谢的小事", "周末安排一次户外散步"],
        riskLevel: "low"
      }
    ],
    conversations: [
      {
        messages: [
          {
            role: "user",
            content: "最近睡觉前还是会想很多事情，心跳有点快。"
          },
          {
            role: "assistant",
            content: "我们一起做 4-7-8 呼吸练习。吸气 4 拍，屏息 7 拍，呼气 8 拍，再告诉我身体的感觉。"
          }
        ]
      }
    ]
  },
  "zh-TW": {
    daily: [
      {
        title: "今日回顧",
        spotlight: "保持呼吸練習，睡前放鬆 5 分鐘。",
        summary: "睡眠品質比昨日提升，焦慮關鍵詞提及次數下降。",
        moodDelta: 1
      },
      {
        title: "昨日總結",
        spotlight: "辨識壓力來源，記錄兩次情緒波動。",
        summary: "及時覺察到與工作相關的焦慮，開始記錄觸發事件與自我對話。",
        moodDelta: 0
      },
      {
        title: "三日回顧",
        spotlight: "完成正念練習，情緒恢復更快。",
        summary: "保持 10 分鐘正念觀察，焦慮恢復時間由 3 小時縮短為 90 分鐘。",
        moodDelta: 1
      }
    ],
    weekly: [
      {
        themes: ["壓力管理", "睡眠節律"],
        highlights: "連續三晚實踐睡前放鬆儀式，入睡時間提早 15 分鐘。",
        actionItems: ["睡前寫下三件感謝的小事", "週末安排一次戶外散步"],
        riskLevel: "low"
      }
    ],
    conversations: [
      {
        messages: [
          {
            role: "user",
            content: "最近睡前還是會想很多事情，心跳有點快。"
          },
          {
            role: "assistant",
            content: "一起做 4-7-8 呼吸練習吧。吸氣 4 拍，憋氣 7 拍，吐氣 8 拍，再告訴我身體的感覺。"
          }
        ]
      }
    ]
  },
  "en-US": {
    daily: [
      {
        title: "Today’s reflection",
        spotlight: "Keep up the breathing practice and give yourself 5 minutes to unwind before bed.",
        summary: "Sleep quality improved compared to yesterday and anxiety keywords showed fewer mentions.",
        moodDelta: 1
      },
      {
        title: "Yesterday’s recap",
        spotlight: "Noticed stress triggers and logged two mood swings.",
        summary: "Work-related anxiety was caught early and you started capturing triggers with supportive self-talk.",
        moodDelta: 0
      },
      {
        title: "Three-day review",
        spotlight: "Completed a mindfulness exercise and recovery is getting faster.",
        summary: "Maintained a 10-minute mindful check-in and shortened recovery time from 3 hours to 90 minutes.",
        moodDelta: 1
      }
    ],
    weekly: [
      {
        themes: ["Stress management", "Sleep rhythm"],
        highlights: "Kept a three-night bedtime wind-down and now fall asleep about 15 minutes faster.",
        actionItems: ["Write down three things you’re grateful for before bed", "Plan one outdoor walk this weekend"],
        riskLevel: "low"
      }
    ],
    conversations: [
      {
        messages: [
          {
            role: "user",
            content: "Lately I keep thinking a lot before bed and my heart races a little."
          },
          {
            role: "assistant",
            content: "Let’s try a 4-7-8 breathing exercise together. Inhale for 4 counts, hold for 7, exhale for 8, then tell me how your body feels."
          }
        ]
      }
    ]
  },
  "ru-RU": {
    daily: [
      {
        title: "Сегодняшний обзор",
        spotlight: "Продолжайте дыхательную практику и выделите 5 минут на расслабление перед сном.",
        summary: "Качество сна улучшилось по сравнению со вчерашним днём, тревожные слова встречаются реже.",
        moodDelta: 1
      },
      {
        title: "Вчерашние итоги",
        spotlight: "Отмечены триггеры, записаны два всплеска эмоций.",
        summary: "Рабочую тревогу удалось заметить вовремя, вы начали фиксировать триггеры и поддерживающий внутренний диалог.",
        moodDelta: 0
      },
      {
        title: "Трёхдневный взгляд",
        spotlight: "Провели практику осознанности, восстановление идёт быстрее.",
        summary: "Сохраняли 10 минут осознанного наблюдения и сократили время восстановления с 3 часов до 90 минут.",
        moodDelta: 1
      }
    ],
    weekly: [
      {
        themes: ["Управление стрессом", "Режим сна"],
        highlights: "Три вечера подряд выполняли расслабляющий ритуал перед сном — засыпаете примерно на 15 минут быстрее.",
        actionItems: ["Перед сном записать три вещи, за которые вы благодарны", "Запланировать прогулку на свежем воздухе в эти выходные"],
        riskLevel: "low"
      }
    ],
    conversations: [
      {
        messages: [
          {
            role: "user",
            content: "В последнее время перед сном опять много думаю, сердце бьётся быстрее."
          },
          {
            role: "assistant",
            content: "Давайте попробуем дыхание 4-7-8. Вдыхайте 4 счёта, задержите на 7, выдыхайте 8, а потом расскажите, что чувствуете."
          }
        ]
      }
    ]
  }
};

function resolveFallbackLocale(locale: string): FallbackLocale {
  const normalized = (locale ?? "").toLowerCase();
  if (normalized.startsWith("zh-tw") || normalized.startsWith("zh_hant")) {
    return "zh-TW";
  }
  if (normalized.startsWith("ru")) {
    return "ru-RU";
  }
  if (normalized.startsWith("en")) {
    return "en-US";
  }
  return "zh-CN";
}

function createFallbackReports(locale: string): JourneyReportsResponse {
  const today = new Date();
  const template = JOURNEY_FALLBACK_COPY[resolveFallbackLocale(locale)] ?? JOURNEY_FALLBACK_COPY["zh-CN"];

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
