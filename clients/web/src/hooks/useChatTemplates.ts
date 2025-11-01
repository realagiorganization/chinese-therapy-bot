import { useCallback, useEffect, useRef, useState } from "react";

import { loadChatTemplates } from "../api/templates";
import type { ChatTemplate } from "../api/types";

type FetchStatus = "idle" | "loading" | "success" | "error";

export type UseChatTemplatesResult = {
  status: FetchStatus;
  templates: ChatTemplate[];
  topics: string[];
  error: string | null;
  selectedTopic: string | null;
  setSelectedTopic: (topic: string | null) => void;
  refetch: () => void;
};

export function useChatTemplates(locale: string): UseChatTemplatesResult {
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [templates, setTemplates] = useState<ChatTemplate[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedTopic, setSelectedTopicState] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);

  const setSelectedTopic = useCallback((topic: string | null) => {
    setSelectedTopicState((previous) => {
      if (previous === topic || (previous === null && topic === "")) {
        return previous;
      }
      return topic ?? null;
    });
  }, []);

  const refetch = useCallback(() => {
    setRefreshToken((token) => token + 1);
  }, []);

  useEffect(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setStatus("loading");
    setError(null);

    loadChatTemplates({
      locale,
      topic: selectedTopic ?? undefined,
      limit: 6,
      signal: controller.signal
    })
      .then((payload) => {
        if (controller.signal.aborted) {
          return;
        }
        setTemplates(payload.templates);
        setTopics(payload.topics);
        setStatus("success");
        setError(null);

        if (selectedTopic && !payload.topics.includes(selectedTopic)) {
          setSelectedTopic(null);
        }
      })
      .catch((caught) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = caught instanceof Error ? caught.message : String(caught);
        setError(message);
        setStatus("error");
      });

    return () => {
      controller.abort();
    };
  }, [locale, selectedTopic, refreshToken, setSelectedTopic]);

  return {
    status,
    templates,
    topics,
    error,
    selectedTopic,
    setSelectedTopic,
    refetch
  };
}
