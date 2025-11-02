import { apiRequest } from "./api/client";
import type { ChatMessage, ChatTurnResponse } from "../types/chat";

type ApiChatResponse = {
  session_id: string;
  reply: {
    role: string;
    content: string;
    created_at: string;
  };
  recommended_therapist_ids: string[];
  recommendations: {
    id: string;
    name: string;
    expertise: string[];
    summary: string;
    avatar_url?: string | null;
  }[];
  memory_highlights: {
    summary: string;
    keywords: string[];
  }[];
  resolved_locale?: string;
  locale?: string;
};

export type SendMessageParams = {
  accessToken: string;
  userId: string;
  sessionId?: string;
  message: string;
  locale: string;
};

export async function sendMessage(
  params: SendMessageParams,
): Promise<ChatTurnResponse> {
  const response = await apiRequest<ApiChatResponse>("/chat/message", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: {
      user_id: params.userId,
      session_id: params.sessionId,
      message: params.message,
      locale: params.locale,
      enable_streaming: false,
    },
  });

  const reply: ChatMessage = {
    role: response.reply.role === "user" ? "user" : "assistant",
    content: response.reply.content,
    createdAt: response.reply.created_at,
  };

  return {
    sessionId: response.session_id,
    reply,
    recommendedTherapistIds: response.recommended_therapist_ids,
    recommendations: response.recommendations.map((rec) => ({
      id: rec.id,
      name: rec.name,
      expertise: rec.expertise,
      summary: rec.summary,
      avatarUrl: rec.avatar_url ?? undefined,
    })),
    memoryHighlights: response.memory_highlights,
    resolvedLocale: response.resolved_locale ?? response.locale ?? "zh-CN",
  };
}
