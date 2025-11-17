import { apiRequest } from "./api/client";

export type AnalyticsEventPayload = {
  eventType: string;
  userId?: string | null;
  sessionId?: string | null;
  funnelStage?: string | null;
  properties?: Record<string, unknown>;
  occurredAt?: string | Date;
};

function toIsoTimestamp(value?: string | Date | null): string | undefined {
  if (!value) {
    return undefined;
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return value.toISOString();
  } catch {
    return undefined;
  }
}

export async function recordAnalyticsEvent(
  payload: AnalyticsEventPayload,
): Promise<void> {
  const occurredAt = toIsoTimestamp(payload.occurredAt) ?? new Date().toISOString();
  await apiRequest("/analytics/events", {
    method: "POST",
    body: {
      event_type: payload.eventType,
      user_id: payload.userId ?? null,
      session_id: payload.sessionId ?? null,
      funnel_stage: payload.funnelStage ?? null,
      properties: payload.properties ?? {},
      occurred_at: occurredAt,
    },
  });
}
