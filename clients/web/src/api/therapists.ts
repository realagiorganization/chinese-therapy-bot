import type { TherapistSummary } from "./types";

export type TherapistListSource = "api" | "fallback";

export type TherapistListPayload = {
  therapists: TherapistSummary[];
  source: TherapistListSource;
};

const DEFAULT_BASE_URL = "http://localhost:8000";

const FALLBACK_THERAPISTS: TherapistSummary[] = [
  {
    id: "therapist-1",
    name: "刘心语",
    title: "国家二级心理咨询师",
    specialties: ["焦虑调节", "认知行为疗法"],
    languages: ["zh-CN"],
    price: 680,
    recommended: true,
    availability: ["今晚 20:00", "周三 19:30"]
  },
  {
    id: "therapist-2",
    name: "王晨",
    title: "注册家庭治疗师",
    specialties: ["家庭治疗", "青少年成长"],
    languages: ["zh-CN", "en-US"],
    price: 520,
    recommended: false,
    availability: ["周四 21:00"]
  },
  {
    id: "therapist-3",
    name: "李安琪",
    title: "Mindfulness 认证导师",
    specialties: ["正念冥想", "情绪复原"],
    languages: ["zh-CN", "en-US"],
    price: 460,
    recommended: true,
    availability: ["周一 18:30", "周六 10:00"]
  }
];

function resolveBaseUrl(): string {
  const envValue = import.meta.env?.VITE_API_BASE_URL as string | undefined;
  if (!envValue || envValue.trim().length === 0) {
    return DEFAULT_BASE_URL;
  }
  return envValue.replace(/\/$/, "");
}

async function requestTherapists(): Promise<TherapistSummary[]> {
  const baseUrl = resolveBaseUrl();
  const endpoint = `${baseUrl}/api/therapists?locale=zh-CN`;
  const response = await fetch(endpoint, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to load therapists (status ${response.status})`);
  }

  const data = await response.json();
  if (!data || !Array.isArray(data.items)) {
    throw new Error("Therapist API payload missing `items`.");
  }

  return data.items.map((item: any) => ({
    id: item.therapist_id ?? item.id,
    name: item.name,
    title: item.title ?? "",
    specialties: Array.isArray(item.specialties) ? item.specialties : [],
    languages: Array.isArray(item.languages) ? item.languages : [],
    price: typeof item.price_per_session === "number" ? item.price_per_session : 0,
    currency: item.currency ?? "CNY",
    recommended: Boolean(item.is_recommended),
    availability: Array.isArray(item.availability) ? item.availability : []
  }));
}

export async function loadTherapists(): Promise<TherapistListPayload> {
  try {
    const therapists = await requestTherapists();
    return { therapists, source: "api" };
  } catch (error) {
    console.warn("[Therapists] Falling back to seed data:", error);
    return { therapists: FALLBACK_THERAPISTS, source: "fallback" };
  }
}

export { FALLBACK_THERAPISTS };
