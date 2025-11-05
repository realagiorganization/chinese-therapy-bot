import type { TherapistDetail, TherapistSummary } from "./types";
import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asBoolean, asNumber, asRecord, asString, asStringArray } from "./parsing";

export type TherapistListSource = "api" | "fallback";

export type TherapistListPayload = {
  therapists: TherapistSummary[];
  source: TherapistListSource;
};

type FallbackLocale = "zh-CN" | "zh-TW" | "en-US" | "ru-RU";

const THERAPIST_FALLBACK_COPY: Record<FallbackLocale, TherapistDetail[]> = {
  "zh-CN": [
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
  ],
  "zh-TW": [
    {
      id: "therapist-1",
      name: "劉心語",
      title: "國家二級心理諮商師",
      specialties: ["焦慮調節", "認知行為療法"],
      languages: ["zh-CN"],
      price: 680,
      currency: "CNY",
      recommended: true,
      availability: ["今晚 20:00", "週三 19:30"],
      biography: "專注職場壓力管理與情緒調節，善於結合 CBT 與呼吸練習提供實用建議。",
      recommendationReason: "擅長職場焦慮與認知行為療法，符合你近期的壓力主題。"
    },
    {
      id: "therapist-2",
      name: "王晨",
      title: "註冊家庭治療師",
      specialties: ["家庭治療", "青少年成長"],
      languages: ["zh-CN", "en-US"],
      price: 520,
      currency: "CNY",
      recommended: false,
      availability: ["週四 21:00"],
      biography: "多年家庭系統治療經驗，擅長陪伴親子溝通與跨文化家庭議題。",
      recommendationReason: "對家庭溝通議題經驗豐富，適合強化親子支持系統。"
    },
    {
      id: "therapist-3",
      name: "李安琪",
      title: "Mindfulness 認證導師",
      specialties: ["正念冥想", "情緒復原"],
      languages: ["zh-CN", "en-US"],
      price: 460,
      currency: "CNY",
      recommended: true,
      availability: ["週一 18:30", "週六 10:00"],
      biography: "結合正念冥想與心理教育，協助來訪者重建情緒韌性。",
      recommendationReason: "擁有豐富的正念練習經驗，適合協助情緒復原與身心調節。"
    }
  ],
  "en-US": [
    {
      id: "therapist-1",
      name: "刘心语",
      title: "Licensed CBT Counselor",
      specialties: ["Anxiety regulation", "Cognitive Behavioral Therapy"],
      languages: ["zh-CN"],
      price: 680,
      currency: "CNY",
      recommended: true,
      availability: ["Tonight 20:00", "Wednesday 19:30"],
      biography: "Focuses on workplace stress management and emotional regulation, blending CBT with breathing practices for actionable guidance.",
      recommendationReason: "Experienced with workplace anxiety and CBT, closely aligned with your recent pressure themes."
    },
    {
      id: "therapist-2",
      name: "王晨",
      title: "Registered family therapist",
      specialties: ["Family therapy", "Adolescent development"],
      languages: ["zh-CN", "en-US"],
      price: 520,
      currency: "CNY",
      recommended: false,
      availability: ["Thursday 21:00"],
      biography: "Years of family systems therapy supporting parent-child communication and cross-cultural families.",
      recommendationReason: "Deep experience with family communication topics—ideal for strengthening your support network."
    },
    {
      id: "therapist-3",
      name: "李安琪",
      title: "Mindfulness Certified Coach",
      specialties: ["Mindfulness meditation", "Emotional resilience"],
      languages: ["zh-CN", "en-US"],
      price: 460,
      currency: "CNY",
      recommended: true,
      availability: ["Monday 18:30", "Saturday 10:00"],
      biography: "Combines mindfulness practice with psychoeducation to help clients rebuild emotional resilience.",
      recommendationReason: "Extensive mindfulness background makes her a strong partner for emotional recovery and self-regulation."
    }
  ],
  "ru-RU": [
    {
      id: "therapist-1",
      name: "Лю Синьюй",
      title: "Сертифицированный CBT-консультант",
      specialties: ["Регуляция тревоги", "Когнитивно-поведенческая терапия"],
      languages: ["zh-CN"],
      price: 680,
      currency: "CNY",
      recommended: true,
      availability: ["Сегодня 20:00", "Среда 19:30"],
      biography: "Управляет рабочим стрессом и эмоциями, сочетая КПТ и дыхательные практики для прикладных рекомендаций.",
      recommendationReason: "Опыт в теме рабочей тревоги и КПТ соответствует вашим текущим запросам."
    },
    {
      id: "therapist-2",
      name: "Ван Чэнь",
      title: "Семейный терапевт",
      specialties: ["Семейная терапия", "Подростковое развитие"],
      languages: ["zh-CN", "en-US"],
      price: 520,
      currency: "CNY",
      recommended: false,
      availability: ["Четверг 21:00"],
      biography: "Многолетний опыт семейной системной терапии, поддерживает диалог между родителями и детьми, работает с мультикультурными семьями.",
      recommendationReason: "Глубокий опыт в темах семейной коммуникации поможет укрепить вашу систему поддержки."
    },
    {
      id: "therapist-3",
      name: "Ли Анци",
      title: "Сертифицированный тренер по майндфулнесу",
      specialties: ["Майндфулнес-медитация", "Эмоциональная устойчивость"],
      languages: ["zh-CN", "en-US"],
      price: 460,
      currency: "CNY",
      recommended: true,
      availability: ["Понедельник 18:30", "Суббота 10:00"],
      biography: "Совмещает практики осознанности и психообразование, помогая клиентам восстановить эмоциональную устойчивость.",
      recommendationReason: "Большой опыт в майндфулнесе, подходит для поддержки эмоционального восстановления и баланса."
    }
  ]
};

function resolveFallbackLocale(locale: string): FallbackLocale {
  const normalized = (locale ?? "").toLowerCase();
  if (normalized.startsWith("zh-tw") || normalized.startsWith("zh_hant")) {
    return "zh-TW";
  }
  if (normalized.startsWith("ru")) {
    return "ru-RU";
  }
  if (normalized.startsWith("en")) {
    return "en-US";
  }
  return "zh-CN";
}

function getFallbackTherapistDetails(locale: string): TherapistDetail[] {
  const resolved = resolveFallbackLocale(locale);
  const template = THERAPIST_FALLBACK_COPY[resolved] ?? THERAPIST_FALLBACK_COPY["zh-CN"];
  return JSON.parse(JSON.stringify(template)) as TherapistDetail[];
}

function getFallbackTherapists(locale: string): TherapistSummary[] {
  return getFallbackTherapistDetails(locale).map(({ biography, recommendationReason, ...summary }) => summary);
}

function mapSummary(item: unknown): TherapistSummary {
  const data = asRecord(item) ?? {};
  return {
    id: asString(data.therapist_id ?? data.id),
    name: asString(data.name),
    title: asString(data.title),
    specialties: asStringArray(data.specialties),
    languages: asStringArray(data.languages),
    price: asNumber(data.price_per_session ?? data.price),
    currency: asString(data.currency, "CNY") || "CNY",
    recommended: asBoolean(data.is_recommended ?? data.recommended),
    availability: asStringArray(data.availability)
  };
}

function mapDetail(item: unknown): TherapistDetail {
  const data = asRecord(item) ?? {};
  const summary = mapSummary(data);
  return {
    ...summary,
    biography: asString(data.biography),
    recommendationReason: (() => {
      const reason = asString(data.recommendation_reason ?? data.recommendationReason);
      return reason || undefined;
    })()
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
