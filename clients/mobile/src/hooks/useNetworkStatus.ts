import * as Network from "expo-network";
import { useEffect, useRef, useState } from "react";
import { AppState, AppStateStatus } from "react-native";

export type NetworkStatus = {
  isConnected: boolean;
  isInternetReachable: boolean;
  type: Network.NetworkStateType | null;
};

const DEFAULT_STATUS: NetworkStatus = {
  isConnected: true,
  isInternetReachable: true,
  type: null,
};

/**
 * Tracks the current network state with active listeners plus a periodic poll.
 * The periodic poll protects against platform-specific listener gaps when the
 * app resumes from background.
 */
export function useNetworkStatus(pollIntervalMs = 15000): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>(DEFAULT_STATUS);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    async function emitState() {
      try {
        const state = await Network.getNetworkStateAsync();
        if (!isMountedRef.current) {
          return;
        }
        setStatus({
          isConnected: Boolean(state.isConnected),
          isInternetReachable:
            state.isInternetReachable ?? Boolean(state.isConnected),
          type: state.type ?? null,
        });
      } catch {
        if (!isMountedRef.current) {
          return;
        }
        setStatus(DEFAULT_STATUS);
      }
    }

    function schedulePoll() {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      pollTimeoutRef.current = setTimeout(() => {
        emitState().finally(schedulePoll);
      }, pollIntervalMs);
    }

    const appStateSubscription = AppState.addEventListener(
      "change",
      (next: AppStateStatus) => {
        if (next === "active") {
          emitState().catch(() => {
            // Falling back to the periodic poll if the immediate fetch fails.
          });
        }
      },
    );

    emitState().catch(() => {
      // Swallow errors; the listener/poll will update when state becomes available.
    });
    schedulePoll();

    return () => {
      isMountedRef.current = false;
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
      appStateSubscription.remove();
    };
  }, [pollIntervalMs]);

  return status;
}
