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

type FallbackLocale = "zh-CN" | "zh-TW" | "en-US" | "ru-RU";

type ExploreFallbackCopy = {
  modules: ExploreModule[];
};

const EXPLORE_FALLBACK_COPY: Record<FallbackLocale, ExploreFallbackCopy> = {
  "zh-CN": {
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
  },
  "zh-TW": {
    modules: [
      {
        id: "breathing-reset",
        moduleType: "breathing_exercise",
        title: "今日呼吸練習",
        description: "快速緩和心率的放鬆練習，大約 5 分鐘即可完成。",
        cadenceLabel: "4-7-8 呼吸節奏",
        durationMinutes: 5,
        steps: [
          { label: "準備姿勢", instruction: "坐直，放鬆肩頸，閉上眼睛。", durationSeconds: 10 },
          { label: "吸氣 4 拍", instruction: "透過鼻腔緩慢吸氣。", durationSeconds: 16 },
          { label: "屏息 7 拍", instruction: "保持肩膀放鬆，默數 1-7。", durationSeconds: 28 },
          { label: "呼氣 8 拍", instruction: "從嘴巴緩慢吐氣，感受胸腔放鬆。", durationSeconds: 32 }
        ],
        recommendedFrequency: "睡前或焦慮上升時練習 2-3 輪。",
        ctaLabel: "開始練習",
        ctaAction: "/app/practices/breathing"
      },
      {
        id: "psychoeducation",
        moduleType: "psychoeducation",
        title: "療癒知識精選",
        description: "結合常見的睡眠與焦慮主題，為你準備自助工具。",
        resources: [
          {
            id: "micro-steps",
            title: "把焦慮拆成三個微任務",
            summary: "練習記錄觸發點、進行 4-7-8 呼吸、書寫自我肯定語句。",
            readTimeMinutes: 6,
            tags: ["壓力管理", "自我覺察"],
            resourceType: "article"
          },
          {
            id: "sleep-hygiene",
            title: "睡眠節律重建指南",
            summary: "設定固定睡前流程，搭配放鬆訓練讓大腦逐步降溫。",
            readTimeMinutes: 5,
            tags: ["睡眠節律", "放鬆訓練"],
            resourceType: "article"
          },
          {
            id: "body-scan",
            title: "三分鐘身體掃描音頻",
            summary: "快速偵測緊繃部位並搭配呼吸引導釋放壓力。",
            readTimeMinutes: 3,
            tags: ["正念練習"],
            resourceType: "audio"
          }
        ],
        ctaLabel: "查看更多",
        ctaAction: "/app/library"
      },
      {
        id: "trending-topics",
        moduleType: "trending_topics",
        title: "當前關注焦點",
        description: "根據常見對話主題，以下練習最值得繼續跟進。",
        topics: [
          {
            name: "壓力管理",
            momentum: 70,
            trend: "up",
            summary: "焦慮對話頻率增加，搭配呼吸練習能更快穩定心率。"
          },
          {
            name: "睡眠節律",
            momentum: 58,
            trend: "steady",
            summary: "維持固定睡前流程可幫助入睡時間提前。"
          }
        ],
        insights: [
          "保持 10 分鐘放鬆儀式有助於縮短入睡時間。",
          "記錄觸發點並練習 4-7-8 呼吸可在 2 分鐘內穩定心率。"
        ],
        ctaLabel: "查看練習建議",
        ctaAction: "/app/trends"
      }
    ]
  },
  "en-US": {
    modules: [
      {
        id: "breathing-reset",
        moduleType: "breathing_exercise",
        title: "Breathing reset for today",
        description: "A quick calming practice that steadies your heart rate in about five minutes.",
        cadenceLabel: "4-7-8 breathing cadence",
        durationMinutes: 5,
        steps: [
          { label: "Find your posture", instruction: "Sit upright, relax your shoulders, gently close your eyes.", durationSeconds: 10 },
          { label: "Inhale for 4", instruction: "Draw a slow breath through your nose.", durationSeconds: 16 },
          { label: "Hold for 7", instruction: "Keep your shoulders soft while you count to seven.", durationSeconds: 28 },
          { label: "Exhale for 8", instruction: "Release through your mouth and notice ease in your chest.", durationSeconds: 32 }
        ],
        recommendedFrequency: "Repeat 2–3 rounds before bed or whenever anxiety climbs.",
        ctaLabel: "Begin practice",
        ctaAction: "/app/practices/breathing"
      },
      {
        id: "psychoeducation",
        moduleType: "psychoeducation",
        title: "Self-guided essentials",
        description: "Curated resources that support common sleep and anxiety themes.",
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
            summary: "Set a consistent bedtime routine with gentle wind-down rituals.",
            readTimeMinutes: 5,
            tags: ["Sleep routine", "Relaxation"],
            resourceType: "article"
          },
          {
            id: "body-scan",
            title: "Three-minute body scan audio",
            summary: "Check in with tense areas and release them with guided breathing.",
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
          "A 10-minute wind-down routine can shorten the time it takes to fall asleep.",
          "Jotting triggers and practicing 4-7-8 breathing can steady your heart in under two minutes."
        ],
        ctaLabel: "See practice ideas",
        ctaAction: "/app/trends"
      }
    ]
  },
  "ru-RU": {
    modules: [
      {
        id: "breathing-reset",
        moduleType: "breathing_exercise",
        title: "Дыхательная перезагрузка на сегодня",
        description: "Короткая практика, которая за 5 минут помогает успокоить пульс.",
        cadenceLabel: "Ритм дыхания 4-7-8",
        durationMinutes: 5,
        steps: [
          { label: "Подберите позу", instruction: "Сядьте прямо, расслабьте плечи и мягко закройте глаза.", durationSeconds: 10 },
          { label: "Вдох на 4 счёта", instruction: "Медленно вдохните через нос.", durationSeconds: 16 },
          { label: "Задержка на 7 счётов", instruction: "Сохраняйте расслабленные плечи и считайте до семи.", durationSeconds: 28 },
          { label: "Выдох на 8 счётов", instruction: "Медленно выдохните через рот, замечая расслабление в груди.", durationSeconds: 32 }
        ],
        recommendedFrequency: "Повторяйте 2–3 цикла перед сном или при росте тревоги.",
        ctaLabel: "Начать практику",
        ctaAction: "/app/practices/breathing"
      },
      {
        id: "psychoeducation",
        moduleType: "psychoeducation",
        title: "Подборка для само-поддержки",
        description: "Материалы, которые помогают справляться со сном и тревогой.",
        resources: [
          {
            id: "micro-steps",
            title: "Разбиваем тревогу на микро-шаги",
            summary: "Фиксируйте триггеры, пробуйте дыхание 4-7-8 и записывайте поддерживающие фразы.",
            readTimeMinutes: 6,
            tags: ["Управление стрессом", "Самоосознанность"],
            resourceType: "article"
          },
          {
            id: "sleep-hygiene",
            title: "Перезапуск режима сна",
            summary: "Настройте стабильный вечерний ритуал с расслабляющими практиками.",
            readTimeMinutes: 5,
            tags: ["Режим сна", "Расслабление"],
            resourceType: "article"
          },
          {
            id: "body-scan",
            title: "Аудио: трёхминутное сканирование тела",
            summary: "Замечайте напряжение и отпускайте его с помощью дыхания.",
            readTimeMinutes: 3,
            tags: ["Осознанность"],
            resourceType: "audio"
          }
        ],
        ctaLabel: "Открыть материалы",
        ctaAction: "/app/library"
      },
      {
        id: "trending-topics",
        moduleType: "trending_topics",
        title: "Актуальные сферы внимания",
        description: "По свежим диалогам видно, что эти практики стоит продолжать.",
        topics: [
          {
            name: "Управление стрессом",
            momentum: 70,
            trend: "up",
            summary: "Тревожные темы звучат чаще — дыхательные практики помогают быстрее стабилизироваться."
          },
          {
            name: "Режим сна",
            momentum: 58,
            trend: "steady",
            summary: "Фиксированный вечерний ритуал сокращает время засыпания."
          }
        ],
        insights: [
          "10 минут расслабляющего ритуала перед сном сокращают время засыпания.",
          "Записывая триггеры и тренируя дыхание 4-7-8, можно успокоить пульс менее чем за две минуты."
        ],
        ctaLabel: "Посмотреть предложения",
        ctaAction: "/app/trends"
      }
    ]
  }
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

function createFallbackExploreResponse(locale: string): ExploreModulesResponse {
  const resolved = resolveFallbackLocale(locale);
  const template = EXPLORE_FALLBACK_COPY[resolved] ?? EXPLORE_FALLBACK_COPY["zh-CN"];
  const modules = JSON.parse(JSON.stringify(template.modules)) as ExploreModule[];
  return {
    locale: resolved,
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
