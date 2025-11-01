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
