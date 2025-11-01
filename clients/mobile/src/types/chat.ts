import type { TherapistRecommendation } from "./therapists";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

export type ChatTurnResponse = {
  sessionId: string;
  reply: ChatMessage;
  recommendedTherapistIds: string[];
  recommendations: TherapistRecommendation[];
  memoryHighlights: {
    summary: string;
    keywords: string[];
  }[];
};
