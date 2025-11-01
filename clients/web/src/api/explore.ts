import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asNumber, asRecord, asString, asStringArray } from "./parsing";
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

function coerceModuleType(raw: unknown): ExploreModuleType | null {
  const value = typeof raw === "string" ? raw : raw?.toString?.();
  if (value === "breathing_exercise" || value === "psychoeducation" || value === "trending_topics") {
    return value;
  }
  return null;
}

function normalizeBreathingModule(raw: unknown): BreathingModule {
  const data = asRecord(raw) ?? {};
  const steps = asArray(data.steps, (step) => {
    const stepData = asRecord(step);
    if (!stepData) {
      return null;
    }
    return {
      label: asString(stepData.label),
      instruction: asString(stepData.instruction),
      durationSeconds: asNumber(stepData.durationSeconds ?? stepData.duration_seconds)
    };
  });

  return {
    id: asString(data.id, "breathing") || "breathing",
    moduleType: "breathing_exercise",
    title: asString(data.title, "Breathing practice") || "Breathing practice",
    description: asString(data.description),
    featureFlag: asString(data.featureFlag ?? data.feature_flag) || undefined,
    ctaLabel: asString(data.ctaLabel ?? data.cta_label) || undefined,
    ctaAction: asString(data.ctaAction ?? data.cta_action) || undefined,
    durationMinutes: asNumber(data.durationMinutes ?? data.duration_minutes, 5),
    cadenceLabel: asString(data.cadenceLabel ?? data.cadence_label),
    steps,
    recommendedFrequency: asString(data.recommendedFrequency ?? data.recommended_frequency)
  };
}

function normalizePsychoeducationModule(raw: unknown): PsychoeducationModule {
  const data = asRecord(raw) ?? {};
  const resources: PsychoeducationResource[] = asArray(data.resources, (resource) => {
    const resourceData = asRecord(resource);
    if (!resourceData) {
      return null;
    }
    const id =
      asString(resourceData.id) ||
      (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2));
    return {
      id,
      title: asString(resourceData.title),
      summary: asString(resourceData.summary),
      readTimeMinutes: asNumber(resourceData.readTimeMinutes ?? resourceData.read_time_minutes),
      tags: asStringArray(resourceData.tags),
      resourceType: asString(resourceData.resourceType ?? resourceData.resource_type, "article") || "article",
      url: resourceData.url === null ? null : asString(resourceData.url) || null
    };
  });

  return {
    id: asString(data.id, "psychoeducation") || "psychoeducation",
    moduleType: "psychoeducation",
    title: asString(data.title, "Psychoeducation") || "Psychoeducation",
    description: asString(data.description),
    featureFlag: asString(data.featureFlag ?? data.feature_flag) || undefined,
    ctaLabel: asString(data.ctaLabel ?? data.cta_label) || undefined,
    ctaAction: asString(data.ctaAction ?? data.cta_action) || undefined,
    resources
  };
}

function normalizeTrendingModule(raw: unknown): TrendingTopicsModule {
  const data = asRecord(raw) ?? {};
  const topics: TrendingTopic[] = asArray(data.topics, (topic) => {
    const topicData = asRecord(topic);
    if (!topicData) {
      return null;
    }
    const trend =
      topicData.trend === "up" || topicData.trend === "down" || topicData.trend === "steady"
        ? (topicData.trend as TrendingTopic["trend"])
        : "steady";
    const name = asString(topicData.name);
    if (!name) {
      return null;
    }
    return {
      name,
      momentum: asNumber(topicData.momentum),
      trend,
      summary: asString(topicData.summary)
    };
  });

  return {
    id: asString(data.id, "trending") || "trending",
    moduleType: "trending_topics",
    title: asString(data.title, "Trending focus areas") || "Trending focus areas",
    description: asString(data.description),
    featureFlag: asString(data.featureFlag ?? data.feature_flag) || undefined,
    ctaLabel: asString(data.ctaLabel ?? data.cta_label) || undefined,
    ctaAction: asString(data.ctaAction ?? data.cta_action) || undefined,
    topics,
    insights: asStringArray(data.insights)
  };
}

function normalizeModule(raw: unknown): ExploreModule | null {
  const data = asRecord(raw);
  const type = coerceModuleType(data?.moduleType ?? data?.module_type);
  if (!type) {
    return null;
  }

  switch (type) {
    case "breathing_exercise":
      return normalizeBreathingModule(data);
    case "psychoeducation":
      return normalizePsychoeducationModule(data);
    case "trending_topics":
      return normalizeTrendingModule(data);
    default:
      return null;
  }
}

function normalizeResponse(raw: unknown, fallbackLocale: string): ExploreModulesResponse {
  const data = asRecord(raw);
  if (!data) {
    return FALLBACK_RESPONSE;
  }

  const modules = asArray(data.modules, (module) => normalizeModule(module)).filter(
    (module): module is ExploreModule => Boolean(module)
  );

  const evaluatedFlags: Record<string, boolean> = {};
  const flagsRecord = asRecord(data.evaluatedFlags);
  if (flagsRecord) {
    for (const [key, value] of Object.entries(flagsRecord)) {
      evaluatedFlags[key] = Boolean(value);
    }
  }

  return {
    locale: asString(data.locale, fallbackLocale) || fallbackLocale,
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
