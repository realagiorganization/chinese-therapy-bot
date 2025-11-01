import type { TherapistDetail, TherapistSummary } from "./types";
import { getApiBaseUrl, withAuthHeaders } from "./client";

export type TherapistListSource = "api" | "fallback";

export type TherapistListPayload = {
  therapists: TherapistSummary[];
  source: TherapistListSource;
};

const FALLBACK_THERAPIST_DETAILS: TherapistDetail[] = [
  {
    id: "therapist-1",
    name: "刘心语",
    title: "国家二级心理咨询师",
    specialties: ["焦虑调节", "认知行为疗法"],
    languages: ["zh-CN"],
    price: 680,
    currency: "CNY",
    recommended: true,
    availability: ["今晚 20:00", "周三 19:30"],
    biography: "专注职场压力管理与情绪调节，善于结合 CBT 与呼吸练习提供实用建议。",
    recommendationReason: "擅长职场焦虑与认知行为疗法，贴合你近期的压力主题。"
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
    availability: ["周四 21:00"],
    biography: "多年家庭系统治疗经验，擅长陪伴亲子沟通和跨文化家庭议题。",
    recommendationReason: "对家庭沟通议题经验丰富，适合强化亲子支持系统。"
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
    availability: ["周一 18:30", "周六 10:00"],
    biography: "将正念冥想与心理教育结合，帮助来访者重建情绪韧性。",
    recommendationReason: "有丰富的正念练习经验，适合协助情绪复原与身心调节。"
  }
];

const FALLBACK_THERAPISTS: TherapistSummary[] = FALLBACK_THERAPIST_DETAILS.map(
  ({ biography, ...summary }) => summary
);

const FALLBACK_DETAIL_MAP = new Map(
  FALLBACK_THERAPIST_DETAILS.map((detail) => [detail.id, detail])
);

function mapSummary(item: any): TherapistSummary {
  return {
    id: item.therapist_id ?? item.id ?? "",
    name: item.name ?? "",
    title: item.title ?? "",
    specialties: Array.isArray(item.specialties) ? item.specialties : [],
    languages: Array.isArray(item.languages) ? item.languages : [],
    price:
      typeof item.price_per_session === "number"
        ? item.price_per_session
        : Number.parseFloat(item.price_per_session) || 0,
    currency: item.currency ?? "CNY",
    recommended: Boolean(item.is_recommended ?? item.recommended),
    availability: Array.isArray(item.availability) ? item.availability : []
  };
}

function mapDetail(item: any): TherapistDetail {
  const summary = mapSummary(item);
  return {
    ...summary,
    biography: typeof item.biography === "string" ? item.biography : "",
    recommendationReason:
      typeof item.recommendation_reason === "string"
        ? item.recommendation_reason
        : typeof item.recommendationReason === "string"
        ? item.recommendationReason
        : undefined
  };
}

async function requestTherapists(locale = "zh-CN"): Promise<TherapistSummary[]> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/therapists?locale=${encodeURIComponent(locale)}`;
  const response = await fetch(endpoint, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load therapists (status ${response.status})`);
  }

  const data = await response.json();
  if (!data || !Array.isArray(data.items)) {
    throw new Error("Therapist API payload missing `items`.");
  }

  return data.items.map((item: any) => mapSummary(item));
}

async function requestTherapistDetail(therapistId: string, locale = "zh-CN"): Promise<TherapistDetail> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/therapists/${encodeURIComponent(
    therapistId
  )}?locale=${encodeURIComponent(locale)}`;
  const response = await fetch(endpoint, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load therapist detail (status ${response.status})`);
  }

  const data = await response.json();
  if (!data || typeof data !== "object") {
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
    return { therapists: FALLBACK_THERAPISTS, source: "fallback" };
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
    const fallback = FALLBACK_DETAIL_MAP.get(therapistId);
    if (fallback) {
      return fallback;
    }
    const summary = FALLBACK_THERAPISTS.find((item) => item.id === therapistId);
    if (summary) {
      return { ...summary, biography: "" };
    }
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export { FALLBACK_THERAPISTS, FALLBACK_THERAPIST_DETAILS };
