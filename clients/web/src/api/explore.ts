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

const EXPLORE_FALLBACK_FLAGS = {
  explore_breathing: true,
  explore_psychoeducation: true,
  explore_trending: true
} as const;

type ExploreFallbackCopy = {
  modules: ExploreModule[];
};

const EXPLORE_FALLBACK_TEMPLATE: ExploreFallbackCopy = {
  modules: [
    {
      id: "breathing-reset",
      moduleType: "breathing_exercise",
      title: "Breathing reset for today",
      description: "A quick calming practice that steadies your heart rate in about five minutes.",
      cadenceLabel: "4-7-8 breathing cadence",
      durationMinutes: 5,
      steps: [
        {
          label: "Find your posture",
          instruction: "Sit upright, relax your shoulders, gently close your eyes.",
          durationSeconds: 10
        },
        {
          label: "Inhale for 4",
          instruction: "Draw a slow, steady breath through your nose while counting to four.",
          durationSeconds: 16
        },
        {
          label: "Hold for 7",
          instruction: "Keep your shoulders soft and count to seven before releasing.",
          durationSeconds: 28
        },
        {
          label: "Exhale for 8",
          instruction: "Release through your mouth and notice ease returning to your chest.",
          durationSeconds: 32
        }
      ],
      recommendedFrequency: "Repeat two to three rounds before bed or whenever anxiety climbs.",
      ctaLabel: "Begin practice",
      ctaAction: "/app/practices/breathing"
    },
    {
      id: "psychoeducation",
      moduleType: "psychoeducation",
      title: "Self-guided essentials",
      description: "Curated resources that support the most common sleep and anxiety themes.",
      resources: [
        {
          id: "micro-steps",
          title: "Break anxiety into micro steps",
          summary: "Track triggers, practice 4-7-8 breathing, and write a supportive affirmation.",
          readTimeMinutes: 6,
          tags: ["Stress management", "Self-awareness"],
          resourceType: "article"
        },
        {
          id: "sleep-hygiene",
          title: "Sleep rhythm reboot",
          summary: "Set a consistent bedtime routine using gentle wind-down rituals.",
          readTimeMinutes: 5,
          tags: ["Sleep routine", "Relaxation"],
          resourceType: "article"
        },
        {
          id: "body-scan",
          title: "Three-minute body scan audio",
          summary: "Scan for tension and release it with guided breathing cues.",
          readTimeMinutes: 3,
          tags: ["Mindfulness"],
          resourceType: "audio"
        }
      ],
      ctaLabel: "View more",
      ctaAction: "/app/library"
    },
    {
      id: "trending-topics",
      moduleType: "trending_topics",
      title: "Trending focus areas",
      description: "Based on recent conversations, these practices deserve extra attention.",
      topics: [
        {
          name: "Stress management",
          momentum: 70,
          trend: "up",
          summary: "Anxiety mentions are rising; pairing with breathing work eases the spike."
        },
        {
          name: "Sleep rhythm",
          momentum: 58,
          trend: "steady",
          summary: "Keeping a bedtime ritual helps you fall asleep sooner."
        }
      ],
      insights: [
        "A ten-minute wind-down routine can shorten the time it takes to fall asleep.",
        "Jotting triggers and practicing 4-7-8 breathing can steady your heart in under two minutes."
      ],
      ctaLabel: "See practice ideas",
      ctaAction: "/app/trends"
    }
  ]
};

function createFallbackExploreResponse(locale: string): ExploreModulesResponse {
  const modules = JSON.parse(JSON.stringify(EXPLORE_FALLBACK_TEMPLATE.modules)) as ExploreModule[];
  return {
    locale,
    evaluatedFlags: { ...EXPLORE_FALLBACK_FLAGS },
    modules
  };
}

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
    return createFallbackExploreResponse(fallbackLocale);
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
    credentials: "include",
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
      return { ...createFallbackExploreResponse(locale), source: "fallback" };
    }
    return { ...response, source: "api" };
  } catch (error) {
    console.warn("[ExploreModules] Falling back to preset modules:", error);
    return { ...createFallbackExploreResponse(locale), source: "fallback" };
  }
}
