import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asBoolean, asNumber, asRecord, asString, asStringArray } from "./parsing";
import type {
  ChatMessage,
  ChatStreamEvent,
  ChatTurnRequest,
  ChatTurnResponse,
  MemoryHighlight,
  TherapistRecommendationDetail
} from "./types";

type ParsedEvent = {
  event: string | null;
  data: string;
};

function isChatRole(value: unknown): value is ChatMessage["role"] {
  return value === "user" || value === "assistant" || value === "system";
}

function normalizeChatMessage(raw: unknown): ChatMessage {
  const data = asRecord(raw) ?? {};
  const createdAtCandidate = data.created_at ?? data.createdAt;
  const createdAt =
    typeof createdAtCandidate === "string" ? createdAtCandidate : new Date().toISOString();

  return {
    role: isChatRole(data.role) ? data.role : "assistant",
    content: asString(data.content),
    createdAt
  };
}

function normalizeRecommendations(items: unknown): TherapistRecommendationDetail[] {
  return asArray(items, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }

    const matchedKeywordsSource = data.matched_keywords ?? data.matchedKeywords;
    const therapistId = asString(data.therapist_id ?? data.therapistId);

    return {
      therapistId,
      name: asString(data.name),
      title: asString(data.title),
      specialties: asStringArray(data.specialties),
      languages: asStringArray(data.languages),
      pricePerSession: asNumber(data.price_per_session ?? data.pricePerSession),
      currency: asString(data.currency, "CNY") || "CNY",
      isRecommended: asBoolean(data.is_recommended ?? data.isRecommended),
      score: asNumber(data.score),
      reason: asString(data.reason),
      matchedKeywords: asStringArray(matchedKeywordsSource)
    };
  });
}

function normalizeHighlights(items: unknown): MemoryHighlight[] {
  return asArray(items, (entry) => {
    const data = asRecord(entry);
    if (!data) {
      return null;
    }
    return {
      summary: asString(data.summary),
      keywords: asStringArray(data.keywords)
    };
  });
}

function normalizeResponse(payload: unknown): ChatTurnResponse {
  const data = asRecord(payload) ?? {};
  const recommendedIdsSource = data.recommended_therapist_ids ?? data.recommendedTherapistIds;

  return {
    sessionId: asString(data.session_id ?? data.sessionId),
    reply: normalizeChatMessage(data.reply ?? data.message),
    recommendedTherapistIds: asArray(recommendedIdsSource, (id) => {
      const value = asString(id);
      return value ? value : null;
    }),
    recommendations: normalizeRecommendations(data.recommendations),
    memoryHighlights: normalizeHighlights(data.memory_highlights),
    resolvedLocale:
      asString(data.resolved_locale ?? data.locale ?? data.resolvedLocale, "zh-CN") || "zh-CN"
  };
}

function parseSseBuffer(buffer: string): { events: ParsedEvent[]; remainder: string } {
  const events: ParsedEvent[] = [];
  let remaining = buffer;

  while (remaining.includes("\n\n")) {
    const delimiterIndex = remaining.indexOf("\n\n");
    if (delimiterIndex === -1) {
      break;
    }

    const chunk = remaining.slice(0, delimiterIndex);
    remaining = remaining.slice(delimiterIndex + 2);

    if (!chunk.trim()) {
      continue;
    }

    const lines = chunk.split(/\r?\n/);
    let eventName: string | null = null;
    const dataLines: string[] = [];

    for (const line of lines) {
      if (!line || line.startsWith(":")) {
        continue;
      }
      const separator = line.indexOf(":");
      const field = separator === -1 ? line : line.slice(0, separator);
      let value = separator === -1 ? "" : line.slice(separator + 1);
      if (value.startsWith(" ")) {
        value = value.slice(1);
      }
      if (field === "event") {
        eventName = value || null;
      } else if (field === "data") {
        dataLines.push(value);
      }
    }

    events.push({
      event: eventName,
      data: dataLines.join("\n")
    });
  }

  return { events, remainder: remaining };
}

function asJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export async function* streamChatTurn(
  request: ChatTurnRequest,
  options?: { signal?: AbortSignal }
): AsyncGenerator<ChatStreamEvent> {
  const endpoint = `${getApiBaseUrl()}/api/chat/message`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: withAuthHeaders({
      "Content-Type": "application/json",
      Accept: "text/event-stream"
    }),
    body: JSON.stringify({
      user_id: request.userId,
      session_id: request.sessionId ?? null,
      message: request.message,
      locale: request.locale ?? "zh-CN",
      enable_streaming: true
    }),
    signal: options?.signal
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = await response.json();
    yield {
      type: "complete",
      data: normalizeResponse(payload)
    };
    return;
  }

  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let keepReading = true;

  try {
    while (keepReading) {
      const { value, done } = await reader.read();
      if (done) {
        keepReading = false;
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const { events, remainder } = parseSseBuffer(buffer);
      buffer = remainder;

      for (const rawEvent of events) {
        const payload = typeof rawEvent.data === "string" ? asJson(rawEvent.data) : rawEvent.data;
        const payloadRecord = asRecord(payload) ?? {};
        switch (rawEvent.event ?? "") {
          case "session_established":
            yield {
              type: "session",
              data: {
                sessionId: asString(payloadRecord.session_id),
                recommendations: normalizeRecommendations(payloadRecord.recommendations),
                recommendedTherapistIds: asArray(payloadRecord.recommended_therapist_ids, (id) => {
                  const value = asString(id);
                  return value ? value : null;
                }),
                memoryHighlights: normalizeHighlights(payloadRecord.memory_highlights),
                locale: asString(payloadRecord.locale),
                resolvedLocale:
                  asString(
                    payloadRecord.resolved_locale ?? payloadRecord.locale ?? payloadRecord.resolvedLocale
                  ) || undefined
              }
            };
            break;
          case "token":
            yield {
              type: "token",
              data: { delta: asString(payloadRecord.delta) }
            };
            break;
          case "complete":
            yield {
              type: "complete",
              data: normalizeResponse(payloadRecord)
            };
            break;
          case "error":
            yield {
              type: "error",
              data: { detail: asString(payloadRecord.detail, "Streaming error") }
            };
            break;
          default:
            break;
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // ignore release errors
    }
  }
}

export async function sendChatTurn(
  request: ChatTurnRequest,
  options?: { signal?: AbortSignal }
): Promise<ChatTurnResponse> {
  const endpoint = `${getApiBaseUrl()}/api/chat/message`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    body: JSON.stringify({
      user_id: request.userId,
      session_id: request.sessionId ?? null,
      message: request.message,
      locale: request.locale ?? "zh-CN",
      enable_streaming: false
    }),
    signal: options?.signal
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  const payload = await response.json();
  return normalizeResponse(payload);
}
