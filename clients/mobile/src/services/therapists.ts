import { apiRequest } from "./api/client";
import type {
  TherapistDetail,
  TherapistFilters,
  TherapistSummary,
} from "../types/therapists";

export type TherapistListSource = "api" | "fallback";

type TherapistListResponse = {
  items: ApiTherapistSummary[];
};

type ApiTherapistSummary = {
  therapist_id: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  price_per_session: number;
  currency?: string;
  is_recommended?: boolean;
};

type ApiTherapistDetail = ApiTherapistSummary & {
  biography: string;
  availability?: string[];
  recommendation_reason?: string | null;
};

const FALLBACK_THERAPISTS: TherapistDetail[] = [
  {
    id: "therapist-1",
    name: "Liu Xinyu",
    title: "Licensed Counselor (Level II)",
    specialties: ["Anxiety regulation", "Cognitive Behavioral Therapy"],
    languages: ["English", "Mandarin Chinese"],
    price: 680,
    currency: "CNY",
    recommended: true,
    biography:
      "Focuses on workplace stress management and emotion regulation, combining CBT with breathing exercises.",
    availability: ["Tonight 20:00", "Wednesday 19:30"],
    recommendationReason:
      "Strong fit for recent stress topics with CBT and anxiety regulation experience.",
  },
  {
    id: "therapist-2",
    name: "Chen Wang",
    title: "Registered Family Therapist",
    specialties: ["Family therapy", "Adolescent development"],
    languages: ["English", "Mandarin Chinese"],
    price: 520,
    currency: "CNY",
    recommended: false,
    biography:
      "Experienced in family systems therapy, supporting parent–child communication and cross-cultural topics.",
    availability: ["Thursday 21:00"],
    recommendationReason:
      "Deep experience in family communication; good for strengthening parent–child support.",
  },
  {
    id: "therapist-3",
    name: "An Qi Li",
    title: "Certified Mindfulness Instructor",
    specialties: ["Mindfulness meditation", "Emotional resilience"],
    languages: ["English", "Mandarin Chinese"],
    price: 460,
    currency: "CNY",
    recommended: true,
    biography:
      "Combines mindfulness practice with psychoeducation to rebuild emotional resilience.",
    availability: ["Monday 18:30", "Saturday 10:00"],
    recommendationReason:
      "Extensive mindfulness practice, suitable for emotional recovery and regulation.",
  },
];

const FALLBACK_SUMMARIES: TherapistSummary[] = FALLBACK_THERAPISTS.map(
  ({ biography, recommendationReason, availability, ...summary }) => ({
    ...summary,
  }),
);

function mapSummary(payload: ApiTherapistSummary): TherapistSummary {
  return {
    id: payload.therapist_id,
    name: payload.name,
    title: payload.title,
    specialties: payload.specialties ?? [],
    languages: payload.languages ?? [],
    price: payload.price_per_session ?? 0,
    currency: payload.currency ?? "CNY",
    recommended: Boolean(payload.is_recommended),
  };
}

function mapDetail(payload: ApiTherapistDetail): TherapistDetail {
  const summary = mapSummary(payload);
  return {
    ...summary,
    biography: payload.biography ?? "",
    availability: payload.availability ?? [],
    recommendationReason: payload.recommendation_reason ?? undefined,
  };
}

export async function loadTherapists(
  locale = "zh-CN",
): Promise<{ therapists: TherapistSummary[]; source: TherapistListSource }> {
  const params = new URLSearchParams({ locale });

  try {
    const response = await apiRequest<TherapistListResponse>(
      `/therapists?${params.toString()}`,
    );
    const therapists =
      response.items?.map((item) => mapSummary(item)) ?? FALLBACK_SUMMARIES;
    if (!response.items || response.items.length === 0) {
      return { therapists: FALLBACK_SUMMARIES, source: "fallback" };
    }
    return { therapists, source: "api" };
  } catch (error) {
    console.warn("[Therapists] Falling back to seed data:", error);
    return { therapists: FALLBACK_SUMMARIES, source: "fallback" };
  }
}

export async function loadTherapistDetail(
  therapistId: string,
  locale = "zh-CN",
): Promise<TherapistDetail> {
  const params = new URLSearchParams({ locale });

  try {
    const detail = await apiRequest<ApiTherapistDetail>(
      `/therapists/${encodeURIComponent(therapistId)}?${params.toString()}`,
    );
    return mapDetail(detail);
  } catch (error) {
    console.warn("[Therapists] Detail fallback:", error);
    const fallback = FALLBACK_THERAPISTS.find(
      (therapist) => therapist.id === therapistId,
    );
    if (!fallback) {
      throw error instanceof Error
        ? error
        : new Error("Therapist detail unavailable");
    }
    return fallback;
  }
}

export function applyFilters(
  therapists: TherapistSummary[],
  filters: TherapistFilters,
): TherapistSummary[] {
  return therapists.filter((therapist) => {
    if (filters.recommendedOnly && !therapist.recommended) {
      return false;
    }
    if (
      filters.specialty &&
      !therapist.specialties.includes(filters.specialty)
    ) {
      return false;
    }
    if (filters.language && !therapist.languages.includes(filters.language)) {
      return false;
    }
    if (filters.minPrice !== undefined && therapist.price < filters.minPrice) {
      return false;
    }
    if (filters.maxPrice !== undefined && therapist.price > filters.maxPrice) {
      return false;
    }
    return true;
  });
}
