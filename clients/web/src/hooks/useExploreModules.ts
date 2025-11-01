import { useEffect, useMemo, useState } from "react";

import { loadExploreModules } from "../api/explore";
import type { ExploreModule, ExploreModulesResponse } from "../api/types";
import type { ExploreModulesSource } from "../api/explore";
import { ensureUserId } from "../utils/user";

export type ExploreModulesState = {
  modules: ExploreModule[];
  evaluatedFlags: Record<string, boolean>;
  isLoading: boolean;
  error: Error | null;
  source: ExploreModulesSource;
  userId: string;
};

const INITIAL_STATE: ExploreModulesResponse = {
  locale: "zh-CN",
  modules: [],
  evaluatedFlags: {}
};

export function useExploreModules(locale: string): ExploreModulesState {
  const [payload, setPayload] = useState<ExploreModulesResponse>(INITIAL_STATE);
  const [source, setSource] = useState<ExploreModulesSource>("fallback");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [userId] = useState(() => ensureUserId());

  useEffect(() => {
    let cancelled = false;

    async function fetchModules() {
      setIsLoading(true);
      try {
        const response = await loadExploreModules(userId, locale);
        if (!cancelled) {
          setPayload(response);
          setSource(response.source);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setPayload(INITIAL_STATE);
          setSource("fallback");
          setError(err instanceof Error ? err : new Error("Unknown explore modules error"));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchModules();

    return () => {
      cancelled = true;
    };
  }, [locale, userId]);

  const modules = useMemo(() => payload.modules ?? [], [payload.modules]);
  const flags = useMemo(() => payload.evaluatedFlags ?? {}, [payload.evaluatedFlags]);

  return {
    modules,
    evaluatedFlags: flags,
    isLoading,
    error,
    source,
    userId
  };
}
