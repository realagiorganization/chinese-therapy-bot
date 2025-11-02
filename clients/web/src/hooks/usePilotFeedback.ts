import { useCallback, useEffect, useRef, useState } from "react";

import { FALLBACK_PILOT_FEEDBACK_SNAPSHOT, loadPilotFeedbackSnapshot } from "../api/feedback";
import type {
  PilotBacklogItem,
  PilotFeedbackEntry,
  PilotFeedbackSnapshotSource,
  PilotParticipant
} from "../api/types";

type UsePilotFeedbackOptions = {
  cohort?: string;
  limit?: number;
};

export type UsePilotFeedbackResult = {
  backlog: PilotBacklogItem[];
  participants: PilotParticipant[];
  recentFeedback: PilotFeedbackEntry[];
  source: PilotFeedbackSnapshotSource;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
};

const FALLBACK_ERROR = new Error("pilot-feedback-fallback");

export function usePilotFeedback(options: UsePilotFeedbackOptions = {}): UsePilotFeedbackResult {
  const { cohort = "pilot-2025w4", limit = 6 } = options;
  const [backlog, setBacklog] = useState<PilotBacklogItem[]>([]);
  const [participants, setParticipants] = useState<PilotParticipant[]>([]);
  const [recentFeedback, setRecentFeedback] = useState<PilotFeedbackEntry[]>([]);
  const [source, setSource] = useState<PilotFeedbackSnapshotSource>("api");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const mountedRef = useRef<boolean>(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const applySnapshot = useCallback(
    (snapshotSource: PilotFeedbackSnapshotSource, data: Partial<UsePilotFeedbackResult>) => {
      if (!mountedRef.current) {
        return;
      }
      if (data.backlog) {
        setBacklog(data.backlog);
      }
      if (data.participants) {
        setParticipants(data.participants);
      }
      if (data.recentFeedback) {
        setRecentFeedback(data.recentFeedback);
      }
      setSource(snapshotSource);
      if (snapshotSource === "fallback") {
        setError(FALLBACK_ERROR);
      } else {
        setError(null);
      }
    },
    []
  );

  const fetchSnapshot = useCallback(async () => {
    setIsLoading(true);
    try {
      const snapshot = await loadPilotFeedbackSnapshot({ cohort, limit });
      applySnapshot(snapshot.source, {
        backlog: snapshot.backlog,
        participants: snapshot.participants,
        recentFeedback: snapshot.recentFeedback
      });
    } catch (err) {
      console.warn("[PilotFeedback] Unable to load live data. Showing fallback snapshot.", err);
      applySnapshot("fallback", {
        backlog: FALLBACK_PILOT_FEEDBACK_SNAPSHOT.backlog,
        participants: FALLBACK_PILOT_FEEDBACK_SNAPSHOT.participants,
        recentFeedback: FALLBACK_PILOT_FEEDBACK_SNAPSHOT.recentFeedback
      });
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [applySnapshot, cohort, limit]);

  useEffect(() => {
    fetchSnapshot().catch((err) => {
      console.error("[PilotFeedback] Unexpected error loading snapshot:", err);
    });
  }, [fetchSnapshot]);

  const refresh = useCallback(async () => {
    await fetchSnapshot();
  }, [fetchSnapshot]);

  return {
    backlog,
    participants,
    recentFeedback,
    source,
    isLoading,
    error,
    refresh
  };
}
