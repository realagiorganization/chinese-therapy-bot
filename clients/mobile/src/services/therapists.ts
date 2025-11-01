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
    name: "刘心语",
    title: "国家二级心理咨询师",
    specialties: ["焦虑调节", "认知行为疗法"],
    languages: ["zh-CN"],
    price: 680,
    currency: "CNY",
    recommended: true,
    biography:
      "专注职场压力管理与情绪调节，善于结合 CBT 与呼吸练习提供实用建议。",
    availability: ["今晚 20:00", "周三 19:30"],
    recommendationReason: "擅长职场焦虑与认知行为疗法，贴合你近期的压力主题。",
  },
  {
    id: "therapist-2",
    name: "王晨",
    title: "注册家庭治疗师",
    specialties: ["家庭治疗", "青少年成长"],
    languages: ["zh-CN", "en-US"],
    price: 520,
    currency: "CNY",
    recommended: false,
    biography: "多年家庭系统治疗经验，擅长陪伴亲子沟通和跨文化家庭议题。",
    availability: ["周四 21:00"],
    recommendationReason: "对家庭沟通议题经验丰富，适合强化亲子支持系统。",
  },
  {
    id: "therapist-3",
    name: "李安琪",
    title: "Mindfulness 认证导师",
    specialties: ["正念冥想", "情绪复原"],
    languages: ["zh-CN", "en-US"],
    price: 460,
    currency: "CNY",
    recommended: true,
    biography: "将正念冥想与心理教育结合，帮助来访者重建情绪韧性。",
    availability: ["周一 18:30", "周六 10:00"],
    recommendationReason: "有丰富的正念练习经验，适合协助情绪复原与身心调节。",
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
