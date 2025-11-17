import type { TherapistRecommendation } from "../types/therapists";

export type ApiTherapistRecommendation = {
  therapist_id?: string;
  id?: string;
  name?: string;
  title?: string;
  specialties?: string[];
  expertise?: string[];
  languages?: string[];
  price_per_session?: number;
  price?: number;
  currency?: string;
  is_recommended?: boolean;
  recommended?: boolean;
  score?: number;
  reason?: string;
  summary?: string;
  matched_keywords?: string[];
  matchedKeywords?: string[];
  avatar_url?: string | null;
  avatarUrl?: string;
};

function clampScore(value: number | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return value;
}

export function normalizeTherapistRecommendation(
  payload: ApiTherapistRecommendation | TherapistRecommendation,
): TherapistRecommendation {
  if (isTherapistRecommendation(payload)) {
    return {
      ...payload,
      reason: payload.reason ?? "",
      matchedKeywords: payload.matchedKeywords ?? [],
      title: payload.title ?? "",
      avatarUrl: payload.avatarUrl,
    };
  }

  const specialties = payload.specialties ?? payload.expertise ?? [];
  const fallbackId =
    payload.therapist_id ?? payload.id ?? payload.name ?? "therapist-fallback";

  return {
    id: fallbackId,
    name: payload.name ?? "MindWell Therapist",
    title: payload.title ?? "",
    specialties,
    languages: payload.languages ?? [],
    price: payload.price_per_session ?? payload.price ?? 0,
    currency: payload.currency ?? "CNY",
    recommended: Boolean(payload.is_recommended ?? payload.recommended ?? false),
    score: clampScore(payload.score),
    reason: payload.reason ?? payload.summary ?? "",
    matchedKeywords:
      payload.matched_keywords ?? payload.matchedKeywords ?? [...specialties],
    avatarUrl: payload.avatar_url ?? payload.avatarUrl ?? undefined,
  };
}

export function normalizeTherapistRecommendations(
  list: (ApiTherapistRecommendation | TherapistRecommendation)[] | undefined,
): TherapistRecommendation[] {
  if (!Array.isArray(list)) {
    return [];
  }
  return list.map((item) => normalizeTherapistRecommendation(item));
}

function isTherapistRecommendation(
  payload: ApiTherapistRecommendation | TherapistRecommendation,
): payload is TherapistRecommendation {
  return (
    "score" in payload &&
    typeof payload.score === "number" &&
    "matchedKeywords" in payload &&
    Array.isArray(payload.matchedKeywords)
  );
}
