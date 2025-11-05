import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asNumber, asRecord, asString, asStringArray } from "./parsing";
import type {
  PilotUATBacklogItem,
  PilotUATBacklogResponse,
  PilotUATGroupSummary,
  PilotUATIssueSummary,
  PilotUATSessionSummary
} from "./types";

export type UATInsightsSource = "api" | "fallback";

export type UATInsightsPayload = {
  source: UATInsightsSource;
  summary: PilotUATSessionSummary;
  backlog: PilotUATBacklogResponse;
};

function asOptionalNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function normalizeIssueSummaries(raw: unknown): PilotUATIssueSummary[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const severity = asString(data.severity ?? data.Severity);
    const count = asNumber(data.count ?? data.Count, -1);
    if (!severity || count < 0) {
      return null;
    }
    return {
      severity,
      count
    };
  });
}

function normalizeGroupSummaries(raw: unknown): PilotUATGroupSummary[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const key = asString(data.key ?? data.Key);
    if (!key) {
      return null;
    }
    return {
      key,
      total: asNumber(data.total ?? data.Total, 0),
      averageSatisfaction: asOptionalNumber(data.averageSatisfaction ?? data.average_satisfaction),
      averageTrust: asOptionalNumber(data.averageTrust ?? data.average_trust)
    };
  });
}

function normalizeSummary(raw: unknown): PilotUATSessionSummary {
  const data = asRecord(raw);
  if (!data) {
    throw new Error("Invalid UAT summary payload");
  }
  return {
    totalSessions: asNumber(data.totalSessions ?? data.total_sessions, 0),
    distinctParticipants: asNumber(data.distinctParticipants ?? data.distinct_participants, 0),
    averageSatisfaction: asOptionalNumber(data.averageSatisfaction ?? data.average_satisfaction),
    averageTrust: asOptionalNumber(data.averageTrust ?? data.average_trust),
    sessionsWithBlockers: asNumber(data.sessionsWithBlockers ?? data.sessions_with_blockers, 0),
    issuesBySeverity: normalizeIssueSummaries(data.issuesBySeverity ?? data.issues_by_severity),
    sessionsByPlatform: normalizeGroupSummaries(data.sessionsByPlatform ?? data.sessions_by_platform),
    sessionsByEnvironment: normalizeGroupSummaries(
      data.sessionsByEnvironment ?? data.sessions_by_environment
    )
  };
}

function normalizeBacklogItems(raw: unknown): PilotUATBacklogItem[] {
  return asArray(raw, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const title = asString(data.title);
    if (!title) {
      return null;
    }
    const latestSessionDate =
      asString(data.latestSessionDate ?? data.latest_session_date) || new Date().toISOString();
    return {
      title,
      severity: asString(data.severity ?? "unspecified"),
      occurrences: asNumber(data.occurrences ?? data.occurrences_count ?? data.count, 0),
      affectedParticipants: asNumber(
        data.affectedParticipants ?? data.affected_participants ?? data.participants,
        0
      ),
      latestSessionDate,
      sampleNotes: asStringArray(data.sampleNotes ?? data.sample_notes),
      actionItems: asStringArray(data.actionItems ?? data.action_items)
    };
  });
}

function normalizeBacklog(raw: unknown): PilotUATBacklogResponse {
  const data = asRecord(raw);
  if (!data) {
    throw new Error("Invalid UAT backlog payload");
  }
  return {
    total: asNumber(data.total, 0),
    items: normalizeBacklogItems(data.items)
  };
}

const NOW_ISO = new Date().toISOString();

const FALLBACK_SUMMARY: PilotUATSessionSummary = {
  totalSessions: 8,
  distinctParticipants: 6,
  averageSatisfaction: 4.2,
  averageTrust: 4.0,
  sessionsWithBlockers: 2,
  issuesBySeverity: [
    { severity: "high", count: 2 },
    { severity: "medium", count: 4 },
    { severity: "low", count: 3 }
  ],
  sessionsByPlatform: [
    { key: "ios", total: 5, averageSatisfaction: 4.4, averageTrust: 4.2 },
    { key: "android", total: 3, averageSatisfaction: 3.8, averageTrust: 3.7 }
  ],
  sessionsByEnvironment: [
    { key: "production", total: 6, averageSatisfaction: 4.3, averageTrust: 4.1 },
    { key: "staging", total: 2, averageSatisfaction: 3.7, averageTrust: 3.5 }
  ]
};

const FALLBACK_BACKLOG: PilotUATBacklogResponse = {
  total: 3,
  items: [
    {
      title: "语音输入偶发中断",
      severity: "high",
      occurrences: 3,
      affectedParticipants: 2,
      latestSessionDate: NOW_ISO,
      sampleNotes: ["语音识别到第 20 秒自动停止，需要重新录音。"],
      actionItems: ["排查 Expo Speech 模块在弱网下的重试逻辑。"]
    },
    {
      title: "旅程报告加载缓慢",
      severity: "medium",
      occurrences: 2,
      affectedParticipants: 2,
      latestSessionDate: NOW_ISO,
      sampleNotes: ["周报页加载超过 5 秒，用户误以为失败。"],
      actionItems: ["添加加载占位与重试提示。"]
    },
    {
      title: "推荐理由文案不够具体",
      severity: "low",
      occurrences: 2,
      affectedParticipants: 1,
      latestSessionDate: NOW_ISO,
      sampleNotes: ["希望看到咨询师擅长的案例，而不是泛化描述。"],
      actionItems: ["补充标签映射示例，更新提示模板。"]
    }
  ]
};

export const FALLBACK_UAT_INSIGHTS: UATInsightsPayload = {
  source: "fallback",
  summary: FALLBACK_SUMMARY,
  backlog: FALLBACK_BACKLOG
};

async function requestSummary(params: URLSearchParams): Promise<PilotUATSessionSummary> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/uat/sessions/summary?${params.toString()}`;
  const response = await fetch(endpoint, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch pilot UAT summary (${response.status})`);
  }
  const payload = await response.json();
  return normalizeSummary(payload);
}

async function requestBacklog(params: URLSearchParams): Promise<PilotUATBacklogResponse> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/uat/sessions/backlog?${params.toString()}`;
  const response = await fetch(endpoint, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch pilot UAT backlog (${response.status})`);
  }
  const payload = await response.json();
  return normalizeBacklog(payload);
}

export type LoadUATInsightsParams = {
  cohort?: string;
  environment?: string;
};

export async function loadUATInsights(
  params: LoadUATInsightsParams = {}
): Promise<UATInsightsPayload> {
  const searchParams = new URLSearchParams();
  if (params.cohort) {
    searchParams.set("cohort", params.cohort);
  }
  if (params.environment) {
    searchParams.set("environment", params.environment);
  }

  try {
    const [summary, backlog] = await Promise.all([
      requestSummary(searchParams),
      requestBacklog(searchParams)
    ]);
    return {
      source: "api",
      summary,
      backlog
    };
  } catch (error) {
    console.warn("Falling back to seed pilot UAT insights", error);
    return FALLBACK_UAT_INSIGHTS;
  }
}
