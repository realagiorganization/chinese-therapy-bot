import type { TherapistDetail, TherapistSummary } from "./types";
import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asBoolean, asNumber, asRecord, asString, asStringArray } from "./parsing";

export type TherapistListSource = "api" | "fallback";

export type TherapistListPayload = {
  therapists: TherapistSummary[];
  source: TherapistListSource;
};

const THERAPIST_FALLBACK_TEMPLATE: TherapistDetail[] = [
  {
    id: "therapist-1",
    name: "Avery Chen",
    title: "Licensed CBT counselor",
    specialties: ["Anxiety regulation", "Cognitive behavioural therapy"],
    languages: ["en-US", "zh-CN"],
    price: 680,
    currency: "CNY",
    recommended: true,
    availability: ["Monday 18:30", "Thursday 19:30"],
    biography:
      "Supports professionals navigating workplace stress with CBT techniques and paced breathing exercises.",
    recommendationReason:
      "Experienced with performance anxiety and cognitive reframing, matching your recent themes."
  },
  {
    id: "therapist-2",
    name: "Morgan Li",
    title: "Registered family therapist",
    specialties: ["Family therapy", "Adolescent development"],
    languages: ["en-US", "zh-CN"],
    price: 520,
    currency: "CNY",
    recommended: false,
    availability: ["Wednesday 20:00", "Saturday 10:00"],
    biography:
      "Guides families through communication challenges with systemic therapy, blending cross-cultural insight.",
    recommendationReason:
      "Ideal for strengthening your support network and building rituals that reduce evening stress."
  },
  {
    id: "therapist-3",
    name: "Lena Park",
    title: "Mindfulness certified coach",
    specialties: ["Mindfulness meditation", "Emotional resilience"],
    languages: ["en-US", "ko-KR"],
    price: 460,
    currency: "CNY",
    recommended: true,
    availability: ["Tuesday 18:00", "Friday 09:30"],
    biography:
      "Combines mindfulness practice with psychoeducation to help clients rebuild sustainable emotional habits.",
    recommendationReason:
      "Strong companion for reinforcing your breathing practice and capturing reflections after each session."
  }
];

function getFallbackTherapistDetails(locale: string): TherapistDetail[] {
  void locale;
  return JSON.parse(JSON.stringify(THERAPIST_FALLBACK_TEMPLATE)) as TherapistDetail[];
}

function getFallbackTherapists(locale: string): TherapistSummary[] {
  return getFallbackTherapistDetails(locale).map(({ biography, ...summary }) => summary);
}

function mapSummary(item: unknown): TherapistSummary {
  const data = asRecord(item) ?? {};
  const rawReason = asString(data.recommendation_reason ?? data.recommendationReason);
  return {
    id: asString(data.therapist_id ?? data.id),
    name: asString(data.name),
    title: asString(data.title),
    specialties: asStringArray(data.specialties),
    languages: asStringArray(data.languages),
    price: asNumber(data.price_per_session ?? data.price),
    currency: asString(data.currency, "CNY") || "CNY",
    recommended: asBoolean(data.is_recommended ?? data.recommended),
    availability: asStringArray(data.availability),
    recommendationReason: rawReason || undefined
  };
}

function mapDetail(item: unknown): TherapistDetail {
  const data = asRecord(item) ?? {};
  const summary = mapSummary(data);
  return {
    ...summary,
    biography: asString(data.biography)
  };
}

async function requestTherapists(locale = "zh-CN"): Promise<TherapistSummary[]> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/therapists?locale=${encodeURIComponent(locale)}`;
  const response = await fetch(endpoint, {
    credentials: "include",
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load therapists (status ${response.status})`);
  }

  const payload = asRecord((await response.json()) as unknown);
  if (!payload) {
    throw new Error("Therapist API payload missing `items`.");
  }
  const items = asArray(payload.items, (item) => mapSummary(item));
  if (items.length === 0) {
    throw new Error("Therapist API payload missing `items`.");
  }

  return items;
}

async function requestTherapistDetail(therapistId: string, locale = "zh-CN"): Promise<TherapistDetail> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/therapists/${encodeURIComponent(
    therapistId
  )}?locale=${encodeURIComponent(locale)}`;
  const response = await fetch(endpoint, {
    credentials: "include",
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load therapist detail (status ${response.status})`);
  }

  const data = asRecord((await response.json()) as unknown);
  if (!data) {
    throw new Error("Therapist detail payload is empty.");
  }

  return mapDetail(data);
}

export async function loadTherapists(locale = "zh-CN"): Promise<TherapistListPayload> {
  try {
    const therapists = await requestTherapists(locale);
    return { therapists, source: "api" };
  } catch (error) {
    console.warn("[Therapists] Falling back to seed data:", error);
    return { therapists: getFallbackTherapists(locale), source: "fallback" };
  }
}

export async function loadTherapistDetail(
  therapistId: string,
  locale = "zh-CN"
): Promise<TherapistDetail> {
  try {
    return await requestTherapistDetail(therapistId, locale);
  } catch (error) {
    console.warn("[Therapists] Falling back to detail seed data:", error);
    const fallbackDetails = getFallbackTherapistDetails(locale);
    const fallback = fallbackDetails.find((detail) => detail.id === therapistId);
    if (fallback) {
      return fallback;
    }
    const summary = getFallbackTherapists(locale).find((item) => item.id === therapistId);
    if (summary) {
      return { ...summary, biography: "" };
    }
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export const FALLBACK_THERAPIST_DETAILS = getFallbackTherapistDetails("zh-CN");
export const FALLBACK_THERAPISTS = getFallbackTherapists("zh-CN");
