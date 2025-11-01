import { getApiBaseUrl, withAuthHeaders } from "./client";
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

function normalizeChatMessage(raw: any): ChatMessage {
  const createdAt =
    typeof raw?.created_at === "string"
      ? raw.created_at
      : typeof raw?.createdAt === "string"
        ? raw.createdAt
        : new Date().toISOString();

  return {
    role: (raw?.role ?? "assistant") as ChatMessage["role"],
    content: typeof raw?.content === "string" ? raw.content : "",
    createdAt
  };
}

function normalizeRecommendations(items: any[]): TherapistRecommendationDetail[] {
  return items.map((item) => ({
    therapistId: String(item?.therapist_id ?? item?.therapistId ?? ""),
    name: typeof item?.name === "string" ? item.name : "",
    title: typeof item?.title === "string" ? item.title : "",
    specialties: Array.isArray(item?.specialties) ? item.specialties : [],
    languages: Array.isArray(item?.languages) ? item.languages : [],
    pricePerSession:
      typeof item?.price_per_session === "number"
        ? item.price_per_session
        : Number.parseFloat(item?.price_per_session) || 0,
    currency: typeof item?.currency === "string" ? item.currency : "CNY",
    isRecommended: Boolean(item?.is_recommended ?? item?.isRecommended),
    score: typeof item?.score === "number" ? item.score : 0,
    reason: typeof item?.reason === "string" ? item.reason : "",
    matchedKeywords: Array.isArray(item?.matched_keywords ?? item?.matchedKeywords)
      ? (item?.matched_keywords ?? item?.matchedKeywords).map((keyword: any) => String(keyword))
      : []
  }));
}

function normalizeHighlights(items: any[]): MemoryHighlight[] {
  return items.map((item) => ({
    summary: typeof item?.summary === "string" ? item.summary : "",
    keywords: Array.isArray(item?.keywords) ? item.keywords.map((keyword: any) => String(keyword)) : []
  }));
}

function normalizeResponse(payload: any): ChatTurnResponse {
  return {
    sessionId: String(payload?.session_id ?? payload?.sessionId ?? ""),
    reply: normalizeChatMessage(payload?.reply ?? payload?.message),
    recommendedTherapistIds: Array.isArray(payload?.recommended_therapist_ids ?? payload?.recommendedTherapistIds)
      ? (payload?.recommended_therapist_ids ?? payload?.recommendedTherapistIds).map((id: any) => String(id))
      : [],
    recommendations: normalizeRecommendations(payload?.recommendations ?? []),
    memoryHighlights: normalizeHighlights(payload?.memory_highlights ?? [])
  };
}

function parseSseBuffer(buffer: string): { events: ParsedEvent[]; remainder: string } {
  const events: ParsedEvent[] = [];
  let remaining = buffer;

  while (true) {
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

function asJson(value: string): any {
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

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const { events, remainder } = parseSseBuffer(buffer);
      buffer = remainder;

      for (const rawEvent of events) {
        const payload = typeof rawEvent.data === "string" ? asJson(rawEvent.data) : rawEvent.data;
        switch (rawEvent.event ?? "") {
          case "session_established":
            yield {
              type: "session",
              data: {
                sessionId: String(payload?.session_id ?? ""),
                recommendations: normalizeRecommendations(payload?.recommendations ?? []),
                recommendedTherapistIds: Array.isArray(payload?.recommended_therapist_ids)
                  ? payload.recommended_therapist_ids.map((id: any) => String(id))
                  : [],
                memoryHighlights: normalizeHighlights(payload?.memory_highlights ?? [])
              }
            };
            break;
          case "token":
            yield {
              type: "token",
              data: { delta: typeof payload?.delta === "string" ? payload.delta : "" }
            };
            break;
          case "complete":
            yield {
              type: "complete",
              data: normalizeResponse(payload)
            };
            break;
          case "error":
            yield {
              type: "error",
              data: { detail: typeof payload?.detail === "string" ? payload.detail : "Streaming error" }
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
