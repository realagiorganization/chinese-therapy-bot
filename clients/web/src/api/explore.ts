import { getApiBaseUrl, withAuthHeaders } from "./client";
import type {
  BreathingModule,
  ExploreModule,
  ExploreModulesResponse,
  ExploreModuleType,
  PsychoeducationModule,
  PsychoeducationResource,
  TrendingTopic,
  TrendingTopicsModule
} from "./types";

export type ExploreModulesSource = "api" | "fallback";

export type ExploreModulesPayload = ExploreModulesResponse & {
  source: ExploreModulesSource;
};

const FALLBACK_RESPONSE: ExploreModulesResponse = {
  locale: "zh-CN",
  evaluatedFlags: {
    explore_breathing: true,
    explore_psychoeducation: true,
    explore_trending: true
  },
  modules: [
    {
      id: "breathing-reset",
      moduleType: "breathing_exercise",
      title: "今日呼吸练习",
      description: "快速缓和心率的放松练习，约 5 分钟即可完成。",
      cadenceLabel: "4-7-8 呼吸节奏",
      durationMinutes: 5,
      steps: [
        { label: "准备姿势", instruction: "坐直，放松肩颈，闭上眼睛。", durationSeconds: 10 },
        { label: "吸气 4 拍", instruction: "通过鼻腔缓慢吸气。", durationSeconds: 16 },
        { label: "屏息 7 拍", instruction: "保持肩膀放松，默数 1-7。", durationSeconds: 28 },
        { label: "呼气 8 拍", instruction: "通过嘴巴缓慢呼出，感受胸腔放松。", durationSeconds: 32 }
      ],
      recommendedFrequency: "睡前或焦虑上升时练习 2-3 轮。",
      ctaLabel: "开始练习",
      ctaAction: "/app/practices/breathing"
    },
    {
      id: "psychoeducation",
      moduleType: "psychoeducation",
      title: "疗愈知识精选",
      description: "结合常见的睡眠与焦虑主题，为你准备的自助工具。",
      resources: [
        {
          id: "micro-steps",
          title: "把焦虑拆成三个微任务",
          summary: "练习记录触发点、进行 4-7-8 呼吸、书写自我肯定语句。",
          readTimeMinutes: 6,
          tags: ["压力管理", "自我觉察"],
          resourceType: "article"
        },
        {
          id: "sleep-hygiene",
          title: "睡眠节律重建指南",
          summary: "设定固定睡前流程，配合放松训练让大脑逐步降温。",
          readTimeMinutes: 5,
          tags: ["睡眠节律", "放松训练"],
          resourceType: "article"
        },
        {
          id: "body-scan",
          title: "三分钟身体扫描音频",
          summary: "快速检测身体紧绷部位并搭配呼吸引导释放压力。",
          readTimeMinutes: 3,
          tags: ["正念练习"],
          resourceType: "audio"
        }
      ],
      ctaLabel: "查看更多",
      ctaAction: "/app/library"
    },
    {
      id: "trending-topics",
      moduleType: "trending_topics",
      title: "当前关注焦点",
      description: "基于常见对话主题，以下练习最值得继续跟进。",
      topics: [
        {
          name: "压力管理",
          momentum: 70,
          trend: "up",
          summary: "焦虑对话频率增加，搭配呼吸练习能更快稳定心率。"
        },
        {
          name: "睡眠节律",
          momentum: 58,
          trend: "steady",
          summary: "维持固定睡前流程可帮助入睡时间提前。"
        }
      ],
      insights: [
        "保持 10 分钟放松仪式有助于缩短入睡时间。",
        "记录触发点并进行 4-7-8 呼吸可在 2 分钟内稳定心率。"
      ],
      ctaLabel: "查看练习建议",
      ctaAction: "/app/trends"
    }
  ]
};

function coerceModuleType(raw: any): ExploreModuleType | null {
  const value = typeof raw === "string" ? raw : raw?.toString?.();
  if (value === "breathing_exercise" || value === "psychoeducation" || value === "trending_topics") {
    return value;
  }
  return null;
}

function normalizeBreathingModule(raw: any): BreathingModule {
  const steps = Array.isArray(raw?.steps)
    ? raw.steps.map((step: any) => ({
        label: step.label ?? "",
        instruction: step.instruction ?? "",
        durationSeconds: Number(step.durationSeconds ?? step.duration_seconds ?? 0) || 0
      }))
    : [];

  return {
    id: raw.id ?? "breathing",
    moduleType: "breathing_exercise",
    title: raw.title ?? "Breathing practice",
    description: raw.description ?? "",
    featureFlag: raw.featureFlag ?? raw.feature_flag ?? undefined,
    ctaLabel: raw.ctaLabel ?? raw.cta_label ?? undefined,
    ctaAction: raw.ctaAction ?? raw.cta_action ?? undefined,
    durationMinutes: Number(raw.durationMinutes ?? raw.duration_minutes ?? 5) || 5,
    cadenceLabel: raw.cadenceLabel ?? raw.cadence_label ?? "",
    steps,
    recommendedFrequency: raw.recommendedFrequency ?? raw.recommended_frequency ?? ""
  };
}

function normalizePsychoeducationModule(raw: any): PsychoeducationModule {
  const resources: PsychoeducationResource[] = Array.isArray(raw?.resources)
    ? raw.resources.map((resource: any) => ({
        id: resource.id ?? crypto.randomUUID?.() ?? String(Math.random()),
        title: resource.title ?? "",
        summary: resource.summary ?? "",
        readTimeMinutes: Number(resource.readTimeMinutes ?? resource.read_time_minutes ?? 0) || 0,
        tags: Array.isArray(resource.tags) ? resource.tags : [],
        resourceType: resource.resourceType ?? resource.resource_type ?? "article",
        url: resource.url ?? null
      }))
    : [];

  return {
    id: raw.id ?? "psychoeducation",
    moduleType: "psychoeducation",
    title: raw.title ?? "Psychoeducation",
    description: raw.description ?? "",
    featureFlag: raw.featureFlag ?? raw.feature_flag ?? undefined,
    ctaLabel: raw.ctaLabel ?? raw.cta_label ?? undefined,
    ctaAction: raw.ctaAction ?? raw.cta_action ?? undefined,
    resources
  };
}

function normalizeTrendingModule(raw: any): TrendingTopicsModule {
  const topics: TrendingTopic[] = Array.isArray(raw?.topics)
    ? raw.topics
        .map((topic: any) => ({
          name: topic.name ?? "",
          momentum: Number(topic.momentum ?? 0) || 0,
          trend: topic.trend === "up" || topic.trend === "down" ? topic.trend : "steady",
          summary: topic.summary ?? ""
        }))
        .filter((topic: TrendingTopic) => Boolean(topic.name))
    : [];

  return {
    id: raw.id ?? "trending",
    moduleType: "trending_topics",
    title: raw.title ?? "Trending focus areas",
    description: raw.description ?? "",
    featureFlag: raw.featureFlag ?? raw.feature_flag ?? undefined,
    ctaLabel: raw.ctaLabel ?? raw.cta_label ?? undefined,
    ctaAction: raw.ctaAction ?? raw.cta_action ?? undefined,
    topics,
    insights: Array.isArray(raw?.insights) ? raw.insights : []
  };
}

function normalizeModule(raw: any): ExploreModule | null {
  const type = coerceModuleType(raw?.moduleType ?? raw?.module_type);
  if (!type) {
    return null;
  }

  switch (type) {
    case "breathing_exercise":
      return normalizeBreathingModule(raw);
    case "psychoeducation":
      return normalizePsychoeducationModule(raw);
    case "trending_topics":
      return normalizeTrendingModule(raw);
    default:
      return null;
  }
}

function normalizeResponse(raw: any, fallbackLocale: string): ExploreModulesResponse {
  if (!raw || typeof raw !== "object") {
    return FALLBACK_RESPONSE;
  }

  const modules = Array.isArray(raw.modules)
    ? raw.modules
        .map((module) => normalizeModule(module))
        .filter((module): module is ExploreModule => Boolean(module))
    : [];

  const evaluatedFlags: Record<string, boolean> = {};
  if (raw.evaluatedFlags && typeof raw.evaluatedFlags === "object") {
    for (const [key, value] of Object.entries(raw.evaluatedFlags as Record<string, unknown>)) {
      evaluatedFlags[key] = Boolean(value);
    }
  }

  return {
    locale: raw.locale ?? fallbackLocale,
    modules,
    evaluatedFlags
  };
}

async function requestExploreModules(userId: string, locale: string): Promise<ExploreModulesResponse> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  params.set("userId", userId);
  if (locale) {
    params.set("locale", locale);
  }

  const response = await fetch(`${baseUrl}/api/explore/modules?${params.toString()}`, {
    headers: withAuthHeaders({
      Accept: "application/json"
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to load explore modules (status ${response.status}).`);
  }

  const payload = await response.json();
  return normalizeResponse(payload, locale);
}

export async function loadExploreModules(userId: string, locale: string): Promise<ExploreModulesPayload> {
  try {
    const response = await requestExploreModules(userId, locale);
    if (response.modules.length === 0) {
      return { ...FALLBACK_RESPONSE, locale, source: "fallback" };
    }
    return { ...response, source: "api" };
  } catch (error) {
    console.warn("[ExploreModules] Falling back to preset modules:", error);
    return { ...FALLBACK_RESPONSE, locale, source: "fallback" };
  }
}
