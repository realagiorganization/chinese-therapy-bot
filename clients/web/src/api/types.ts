export type TherapistSummary = {
  id: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  price: number;
  currency?: string;
  recommended: boolean;
  availability: string[];
};

export type TherapistDetail = TherapistSummary & {
  biography: string;
  recommendationReason?: string;
};

export type TherapistFilters = {
  specialty?: string;
  language?: string;
  recommendedOnly?: boolean;
  minPrice?: number;
  maxPrice?: number;
};

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  role: ChatRole;
  content: string;
  createdAt: string;
};

export type MemoryHighlight = {
  summary: string;
  keywords: string[];
};

export type TherapistRecommendationDetail = {
  therapistId: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  pricePerSession: number;
  currency: string;
  isRecommended: boolean;
  score: number;
  reason: string;
  matchedKeywords: string[];
};

export type ChatTurnResponse = {
  sessionId: string;
  reply: ChatMessage;
  recommendedTherapistIds: string[];
  recommendations: TherapistRecommendationDetail[];
  memoryHighlights: MemoryHighlight[];
  resolvedLocale: string;
};

export type ChatTurnRequest = {
  userId: string;
  sessionId?: string;
  message: string;
  locale?: string;
};

export type ChatStreamEvent =
  | {
      type: "session";
      data: {
        sessionId: string;
        recommendations: TherapistRecommendationDetail[];
        recommendedTherapistIds: string[];
        memoryHighlights: MemoryHighlight[];
        locale?: string;
        resolvedLocale?: string;
      };
    }
  | {
      type: "token";
      data: { delta: string };
    }
  | {
      type: "complete";
      data: ChatTurnResponse;
    }
  | {
      type: "error";
      data: { detail: string };
    };

export type DailyJourneyReport = {
  reportDate: string;
  title: string;
  spotlight: string;
  summary: string;
  moodDelta: number;
};

export type WeeklyJourneyReport = {
  weekStart: string;
  themes: string[];
  highlights: string;
  actionItems: string[];
  riskLevel: string;
};

export type JourneyConversationMessage = {
  messageId: string;
  role: ChatRole;
  content: string;
  createdAt: string;
};

export type JourneyConversationSlice = {
  sessionId: string;
  startedAt: string;
  updatedAt: string;
  therapistId?: string | null;
  messages: JourneyConversationMessage[];
};

export type JourneyReportsResponse = {
  daily: DailyJourneyReport[];
  weekly: WeeklyJourneyReport[];
  conversations: JourneyConversationSlice[];
};

export type ExploreModuleType = "breathing_exercise" | "psychoeducation" | "trending_topics";

export type BreathingStep = {
  label: string;
  instruction: string;
  durationSeconds: number;
};

export type BreathingModule = {
  id: string;
  moduleType: "breathing_exercise";
  title: string;
  description: string;
  featureFlag?: string;
  ctaLabel?: string;
  ctaAction?: string;
  durationMinutes: number;
  cadenceLabel: string;
  steps: BreathingStep[];
  recommendedFrequency: string;
};

export type PsychoeducationResource = {
  id: string;
  title: string;
  summary: string;
  readTimeMinutes: number;
  tags: string[];
  resourceType: string;
  url?: string | null;
};

export type PsychoeducationModule = {
  id: string;
  moduleType: "psychoeducation";
  title: string;
  description: string;
  featureFlag?: string;
  ctaLabel?: string;
  ctaAction?: string;
  resources: PsychoeducationResource[];
};

export type TrendingTopic = {
  name: string;
  momentum: number;
  trend: "up" | "steady" | "down";
  summary: string;
};

export type TrendingTopicsModule = {
  id: string;
  moduleType: "trending_topics";
  title: string;
  description: string;
  featureFlag?: string;
  ctaLabel?: string;
  ctaAction?: string;
  topics: TrendingTopic[];
  insights: string[];
};

export type ExploreModule = BreathingModule | PsychoeducationModule | TrendingTopicsModule;

export type ExploreModulesResponse = {
  locale: string;
  modules: ExploreModule[];
  evaluatedFlags: Record<string, boolean>;
};

export type ChatTemplate = {
  id: string;
  topic: string;
  locale: string;
  title: string;
  userPrompt: string;
  assistantExample: string;
  followUpQuestions: string[];
  selfCareTips: string[];
  keywords: string[];
  tags: string[];
};

export type ChatTemplatesResponse = {
  locale: string;
  topics: string[];
  templates: ChatTemplate[];
};
