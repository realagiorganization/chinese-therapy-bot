export type JourneyReportsSource = "api" | "fallback";

export type JourneyConversationMessage = {
  messageId: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
};

export type JourneyConversationSlice = {
  sessionId: string;
  startedAt: string;
  updatedAt: string;
  therapistId: string | null;
  messages: JourneyConversationMessage[];
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
  riskLevel: "low" | "medium" | "high";
};

export type JourneyReportsResponse = {
  daily: DailyJourneyReport[];
  weekly: WeeklyJourneyReport[];
  conversations: JourneyConversationSlice[];
};
