import { getApiBaseUrl, withAuthHeaders } from "./client";
import {
  asArray,
  asNumber,
  asRecord,
  asString,
  asStringArray
} from "./parsing";
import type {
  PilotBacklogItem,
  PilotFeedbackEntry,
  PilotFeedbackSnapshot,
  PilotParticipant
} from "./types";

type SnapshotOptions = {
  cohort?: string;
  limit?: number;
};

const FALLBACK_PILOT_FEEDBACK_SNAPSHOT: PilotFeedbackSnapshot = {
  source: "fallback",
  backlog: [
    {
      label: "语音播报偶发卡顿",
      tag: "voice_playback",
      scenario: "mobile-chat",
      cohorts: ["pilot-2025w4"],
      frequency: 6,
      participantCount: 4,
      followUpCount: 3,
      averageSentiment: 3.2,
      averageTrust: 2.7,
      averageUsability: 2.4,
      priorityScore: 0.78,
      representativeSeverity: "high",
      lastSubmittedAt: "2025-01-22T09:30:00Z",
      highlights: ["语音播报整体舒缓，但偶尔会突然停止。"],
      blockers: ["Android 机型停止后需要重新进入会话才能恢复。"]
    },
    {
      label: "治疗师推荐理由需要更多说明",
      tag: "recommendations",
      scenario: "web-directory",
      cohorts: ["pilot-2025w4"],
      frequency: 4,
      participantCount: 3,
      followUpCount: 1,
      averageSentiment: 3.8,
      averageTrust: 3.1,
      averageUsability: 3.2,
      priorityScore: 0.54,
      representativeSeverity: "medium",
      lastSubmittedAt: "2025-01-20T14:10:00Z",
      highlights: ["整体推荐方向正确。"],
      blockers: ["缺少评分维度说明，想了解具体匹配逻辑。"]
    }
  ],
  participants: [
    {
      id: "fallback-participant-1",
      cohort: "pilot-2025w4",
      fullName: "林安",
      preferredName: "安安",
      displayName: "安安",
      status: "active",
      channel: "mobile",
      tags: ["android", "voice"],
      requiresFollowUp: true,
      lastContactAt: "2025-01-21T12:00:00Z",
      followUpNotes: "等待语音播报补丁，约定修复后一周回访。",
      updatedAt: "2025-01-21T12:05:00Z"
    },
    {
      id: "fallback-participant-2",
      cohort: "pilot-2025w4",
      fullName: "Zoe Chen",
      preferredName: null,
      displayName: "Zoe Chen",
      status: "prospect",
      channel: "web",
      tags: ["recommendation"],
      requiresFollowUp: true,
      lastContactAt: "2025-01-19T09:45:00Z",
      followUpNotes: "需要演示推荐算法解释面板。",
      updatedAt: "2025-01-19T09:50:00Z"
    }
  ],
  recentFeedback: [
    {
      id: "fallback-feedback-1",
      cohort: "pilot-2025w4",
      scenario: "mobile-chat",
      participantAlias: "安安",
      channel: "mobile",
      highlights: "语音播报帮我缓解紧张情绪。",
      blockers: "播放 3 分钟后偶尔卡住，需要重新进入。",
      tags: ["voice", "android"],
      sentimentScore: 4,
      trustScore: 3,
      usabilityScore: 2,
      followUpNeeded: true,
      severity: "high",
      submittedAt: "2025-01-21T11:40:00Z"
    },
    {
      id: "fallback-feedback-2",
      cohort: "pilot-2025w4",
      scenario: "web-directory",
      participantAlias: "Zoe",
      channel: "web",
      highlights: "推荐的治疗师感觉匹配。",
      blockers: "想知道推荐依据，比如擅长主题如何匹配。",
      tags: ["recommendation"],
      sentimentScore: 4,
      trustScore: 3,
      usabilityScore: 3,
      followUpNeeded: false,
      severity: "medium",
      submittedAt: "2025-01-20T08:10:00Z"
    },
    {
      id: "fallback-feedback-3",
      cohort: "pilot-2025w4",
      scenario: "daily-summary",
      participantAlias: "晨曦",
      channel: "mobile",
      highlights: "每日摘要捕捉到关键情绪变化。",
      blockers: null,
      tags: ["summaries"],
      sentimentScore: 5,
      trustScore: 4,
      usabilityScore: 4,
      followUpNeeded: false,
      severity: "low",
      submittedAt: "2025-01-19T17:05:00Z"
    }
  ]
};

function normalizeBacklog(raw: unknown): PilotBacklogItem[] {
  const payload = asRecord(raw);
  const items = payload?.items ?? raw;
  return asArray(items, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const label = asString(data.label);
    if (!label) {
      return null;
    }
    const priorityScore = asNumber(data.priority_score ?? data.priorityScore, 0);
    return {
      label,
      tag: (asString(data.tag) || null) ?? null,
      scenario: (asString(data.scenario) || null) ?? null,
      cohorts: asStringArray(data.cohorts),
      frequency: asNumber(data.frequency, 0),
      participantCount: asNumber(data.participant_count ?? data.participantCount, 0),
      followUpCount: asNumber(data.follow_up_count ?? data.followUpCount, 0),
      averageSentiment: asNumber(data.average_sentiment ?? data.averageSentiment, 0),
      averageTrust: asNumber(data.average_trust ?? data.averageTrust, 0),
      averageUsability: asNumber(data.average_usability ?? data.averageUsability, 0),
      priorityScore,
      representativeSeverity:
        (asString(data.representative_severity ?? data.representativeSeverity) || null) ?? null,
      lastSubmittedAt: asString(
        data.last_submitted_at ?? data.lastSubmittedAt,
        new Date().toISOString()
      ),
      highlights: asStringArray(data.highlights),
      blockers: asStringArray(data.blockers)
    };
  });
}

function normalizeParticipants(raw: unknown): PilotParticipant[] {
  const payload = asRecord(raw);
  const items = payload?.items ?? raw;
  return asArray(items, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const id = asString(data.id);
    if (!id) {
      return null;
    }
    const cohort = asString(data.cohort) || "pilot";
    const fullName = asString(data.full_name ?? data.fullName) || null;
    const preferredName = asString(data.preferred_name ?? data.preferredName) || null;
    const contactEmail = asString(data.contact_email ?? data.contactEmail) || null;
    const displayName =
      preferredName ||
      fullName ||
      contactEmail ||
      asString(data.participant_alias ?? data.participantAlias) ||
      id;
    return {
      id,
      cohort,
      fullName,
      preferredName,
      displayName,
      status: asString(data.status) || "prospect",
      channel: asString(data.channel) || "web",
      tags: asStringArray(data.tags),
      requiresFollowUp: Boolean(data.requires_follow_up ?? data.requiresFollowUp),
      lastContactAt: (asString(data.last_contact_at ?? data.lastContactAt) || null) ?? null,
      followUpNotes: (asString(data.follow_up_notes ?? data.followUpNotes) || null) ?? null,
      updatedAt: asString(data.updated_at ?? data.updatedAt, new Date().toISOString())
    };
  });
}

function normalizeFeedback(raw: unknown): PilotFeedbackEntry[] {
  const payload = asRecord(raw);
  const items = payload?.items ?? raw;
  return asArray(items, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    const id = asString(data.id);
    if (!id) {
      return null;
    }
    return {
      id,
      cohort: asString(data.cohort),
      scenario: (asString(data.scenario) || null) ?? null,
      participantAlias: (asString(data.participant_alias ?? data.participantAlias) || null) ?? null,
      channel: asString(data.channel) || "web",
      highlights: (asString(data.highlights) || null) ?? null,
      blockers: (asString(data.blockers) || null) ?? null,
      tags: asStringArray(data.tags),
      sentimentScore: asNumber(data.sentiment_score ?? data.sentimentScore, 0),
      trustScore: asNumber(data.trust_score ?? data.trustScore, 0),
      usabilityScore: asNumber(data.usability_score ?? data.usabilityScore, 0),
      followUpNeeded: Boolean(data.follow_up_needed ?? data.followUpNeeded),
      severity: (asString(data.severity) || null) ?? null,
      submittedAt: asString(data.submitted_at ?? data.submittedAt, new Date().toISOString())
    };
  });
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to load pilot feedback (${response.status})`);
  }
  return (await response.json()) as unknown;
}

export async function loadPilotFeedbackSnapshot(
  options: SnapshotOptions = {}
): Promise<PilotFeedbackSnapshot> {
  const { cohort = "pilot-2025w4", limit = 6 } = options;
  const baseUrl = getApiBaseUrl();

  const backlogParams = new URLSearchParams();
  if (cohort) {
    backlogParams.set("cohort", cohort);
  }
  backlogParams.set("limit", String(limit));

  const participantParams = new URLSearchParams();
  if (cohort) {
    participantParams.set("cohort", cohort);
  }
  participantParams.set("requires_follow_up", "true");
  participantParams.set("limit", String(limit));

  const feedbackParams = new URLSearchParams();
  if (cohort) {
    feedbackParams.set("cohort", cohort);
  }
  feedbackParams.set("limit", String(limit));

  try {
    const [backlogRaw, participantsRaw, feedbackRaw] = await Promise.all([
      fetchJson(`${baseUrl}/api/feedback/pilot/backlog?${backlogParams.toString()}`),
      fetchJson(`${baseUrl}/api/feedback/pilot/participants?${participantParams.toString()}`),
      fetchJson(`${baseUrl}/api/feedback/pilot?${feedbackParams.toString()}`)
    ]);

    return {
      source: "api",
      backlog: normalizeBacklog(backlogRaw),
      participants: normalizeParticipants(participantsRaw),
      recentFeedback: normalizeFeedback(feedbackRaw)
    };
  } catch (error) {
    console.warn("[PilotFeedback] Falling back to seed data:", error);
    return FALLBACK_PILOT_FEEDBACK_SNAPSHOT;
  }
}

export { FALLBACK_PILOT_FEEDBACK_SNAPSHOT };
