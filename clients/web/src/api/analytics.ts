import { getApiBaseUrl } from "./client";
import { asRecord, asString } from "./parsing";

const ANALYTICS_SESSION_KEY = "mindwell:analytics:session";

type AnalyticsEventPayload = {
  eventType: string;
  funnelStage?: string;
  properties?: Record<string, unknown>;
};

type AnalyticsEventResponse = {
  id: string;
  createdAt: string;
};

function getAnalyticsSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const existing = window.localStorage.getItem(ANALYTICS_SESSION_KEY);
    if (existing) {
      return existing;
    }
    if (typeof crypto?.randomUUID === "function") {
      const generated = crypto.randomUUID();
      window.localStorage.setItem(ANALYTICS_SESSION_KEY, generated);
      return generated;
    }
  } catch {
    // ignore storage failures
  }
  return null;
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function trackAnalyticsEvent(
  payload: AnalyticsEventPayload
): Promise<AnalyticsEventResponse | null> {
  const endpoint = `${getApiBaseUrl()}/api/analytics/events`;
  const sessionId = getAnalyticsSessionId();
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({
        event_type: payload.eventType,
        session_id: sessionId,
        funnel_stage: payload.funnelStage ?? null,
        properties: payload.properties ?? {}
      })
    });
  } catch {
    return null;
  }

  if (!response.ok) {
    return null;
  }

  const data = asRecord(await parseJson(response));
  if (!data) {
    return null;
  }
  return {
    id: asString(data.id),
    createdAt: asString(data.created_at)
  };
}
