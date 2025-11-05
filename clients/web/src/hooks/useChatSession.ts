import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChatError, sendChatTurn, streamChatTurn } from "../api/chat";
import type {
  ChatMessage,
  ChatTurnRequest,
  ChatTurnResponse,
  MemoryHighlight,
  TherapistRecommendationDetail
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type LocalChatMessage = ChatMessage & {
  id: string;
  streaming?: boolean;
};

export type ChatTranscriptMessage = LocalChatMessage;

function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = (Math.random() * 16) | 0;
    const value = character === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function mergeAssistantMessage(
  messages: LocalChatMessage[],
  messageId: string,
  updater: (current: LocalChatMessage) => LocalChatMessage
): LocalChatMessage[] {
  return messages.map((message) =>
    message.id === messageId ? updater(message) : message
  );
}

type ChatSessionState = {
  messages: LocalChatMessage[];
  recommendations: TherapistRecommendationDetail[];
  memoryHighlights: MemoryHighlight[];
  sessionId?: string;
  isStreaming: boolean;
  error: string | null;
  resolvedLocale?: string;
  quotaExceeded: boolean;
};

const INITIAL_STATE: ChatSessionState = {
  messages: [],
  recommendations: [],
  memoryHighlights: [],
  sessionId: undefined,
  isStreaming: false,
  error: null,
  resolvedLocale: undefined,
  quotaExceeded: false
};

export type UseChatSessionResult = {
  messages: LocalChatMessage[];
  sendMessage: (message: string) => Promise<void>;
  cancelStreaming: () => void;
  resetSession: () => void;
  isStreaming: boolean;
  error: string | null;
  clearError: () => void;
  recommendations: TherapistRecommendationDetail[];
  memoryHighlights: MemoryHighlight[];
  sessionId?: string;
  resolvedLocale: string;
  quotaExceeded: boolean;
  dismissQuotaPrompt: () => void;
};

export function useChatSession(locale: string): UseChatSessionResult {
  const [state, setState] = useState<ChatSessionState>(INITIAL_STATE);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { t } = useTranslation();
  const { userId } = useAuth();

  if (!userId) {
    throw new Error("useChatSession доступен только после успешной аутентификации.");
  }

  const translateErrorMessage = useCallback(
    (detail: string, code?: string) => {
      if (code === "chat_tokens_exhausted") {
        return t("chat.errors.tokens_exhausted");
      }
      if (code === "chat_stream_failure") {
        return t("chat.errors.stream_failure");
      }
      if (!detail) {
        return t("chat.errors.generic");
      }
      return detail;
    },
    [t]
  );

  const clearError = useCallback(() => {
    setState((prev) => ({
      ...prev,
      error: null
    }));
  }, []);

  const dismissQuotaPrompt = useCallback(() => {
    setState((prev) => ({
      ...prev,
      quotaExceeded: false
    }));
  }, []);

  const resetSession = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setState(INITIAL_STATE);
  }, []);

  const cancelStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const sendMessage = useCallback(
    async (input: string) => {
      const trimmed = input.trim();
      if (!trimmed) {
        return;
      }

      abortControllerRef.current?.abort();

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const timestamp = new Date().toISOString();
      const userMessage: LocalChatMessage = {
        id: generateUuid(),
        role: "user",
        content: trimmed,
        createdAt: timestamp
      };
      const assistantMessageId = generateUuid();
      const assistantPlaceholder: LocalChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        createdAt: timestamp,
        streaming: true
      };

      const requestLocale = state.resolvedLocale ?? locale;

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, assistantPlaceholder],
        error: null,
        isStreaming: true,
        quotaExceeded: false
      }));

      const request: ChatTurnRequest = {
        userId,
        sessionId: state.sessionId,
        message: trimmed,
        locale: requestLocale
      };

      let streamCompleted = false;
      let aggregated = "";
      let fallbackAttempted = false;

      const applyError = (detail: string, options?: { quota?: boolean; code?: string }) => {
        const message = translateErrorMessage(detail, options?.code);
        streamCompleted = true;
        abortControllerRef.current = null;
        setState((prev) => ({
          ...prev,
          quotaExceeded: prev.quotaExceeded || Boolean(options?.quota),
          isStreaming: false,
          error: message,
          messages: mergeAssistantMessage(prev.messages, assistantMessageId, (current) => ({
            ...current,
            content: message,
            streaming: false
          }))
        }));
      };

      const finalizeFromResponse = (response: ChatTurnResponse) => {
        streamCompleted = true;
        abortControllerRef.current = null;
        setState((prev) => ({
          ...prev,
          sessionId: response.sessionId || prev.sessionId,
          recommendations: response.recommendations,
          memoryHighlights: response.memoryHighlights,
          resolvedLocale: response.resolvedLocale || prev.resolvedLocale || locale,
          messages: mergeAssistantMessage(prev.messages, assistantMessageId, () => ({
            id: assistantMessageId,
            ...response.reply,
            streaming: false
          })),
          isStreaming: false,
          error: null,
          quotaExceeded: false
        }));
      };

      const attemptFallback = async () => {
        if (fallbackAttempted || controller.signal.aborted || streamCompleted) {
          return;
        }
        fallbackAttempted = true;
        try {
          const response = await sendChatTurn(request, { signal: controller.signal });
          finalizeFromResponse(response);
        } catch (fallbackError) {
          if (fallbackError instanceof ChatError && fallbackError.status === 402) {
            applyError(fallbackError.message, true);
          } else if (fallbackError instanceof ChatError) {
            applyError(fallbackError.message);
          } else if (fallbackError instanceof Error) {
            applyError(fallbackError.message);
          } else {
            applyError(String(fallbackError));
          }
        }
      };

      try {
        for await (const event of streamChatTurn(request, { signal: controller.signal })) {
          if (event.type === "session") {
            setState((prev) => ({
              ...prev,
              sessionId: event.data.sessionId || prev.sessionId,
              recommendations: event.data.recommendations,
              memoryHighlights: event.data.memoryHighlights,
              resolvedLocale:
                event.data.resolvedLocale ||
                event.data.locale ||
                prev.resolvedLocale ||
                locale
            }));
          } else if (event.type === "token") {
            aggregated += event.data.delta;
            setState((prev) => ({
              ...prev,
              messages: mergeAssistantMessage(prev.messages, assistantMessageId, (message) => ({
                ...message,
                content: aggregated,
                streaming: true
              }))
            }));
          } else if (event.type === "complete") {
            finalizeFromResponse(event.data);
          } else if (event.type === "error") {
            const code = event.data.code;
            if (code === "chat_stream_failure") {
              await attemptFallback();
              break;
            }
            const isQuotaError = code === "chat_tokens_exhausted";
            applyError(event.data.detail, { quota: isQuotaError, code });
            break;
          }
        }

        if (!streamCompleted && !controller.signal.aborted) {
          await attemptFallback();
        }
      } catch (error) {
        if (controller.signal.aborted) {
          abortControllerRef.current = null;
          setState((prev) => ({
            ...prev,
            isStreaming: false,
            messages: prev.messages.filter((message) => message.id !== assistantMessageId)
          }));
        } else if (error instanceof ChatError) {
          const quotaError = error.status === 402 || error.code === "chat_tokens_exhausted";
          applyError(error.message, { quota: quotaError, code: error.code });
          if (!quotaError) {
            await attemptFallback();
          }
        } else if (error instanceof Error) {
          applyError(error.message);
          await attemptFallback();
        } else {
          applyError(String(error));
          await attemptFallback();
        }
      }
    },
    [locale, state.sessionId, state.resolvedLocale, translateErrorMessage, userId]
  );

  return {
    messages: state.messages,
    sendMessage,
    cancelStreaming,
    resetSession,
    isStreaming: state.isStreaming,
    error: state.error,
    clearError,
    recommendations: state.recommendations,
    memoryHighlights: state.memoryHighlights,
    sessionId: state.sessionId,
    resolvedLocale: state.resolvedLocale ?? locale,
    quotaExceeded: state.quotaExceeded,
    dismissQuotaPrompt
  };
}
