import { useCallback, useEffect } from "react";
import { InteractionManager, Platform } from "react-native";

const DEFAULT_LABEL = "app";

declare global {
  // eslint-disable-next-line no-var
  var __mindwell_app_start: number | undefined;
}

if (typeof globalThis.__mindwell_app_start !== "number") {
  globalThis.__mindwell_app_start = Date.now();
}

const appStart: number = globalThis.__mindwell_app_start;

type StartupProfilerOptions = {
  /**
   * Enable or disable console logging. Defaults to `__DEV__`.
   */
  enabled?: boolean;
  /**
   * Namespace label prepended to each console entry.
   */
  label?: string;
};

function logMetric(label: string, event: string, deltaMs: number) {
  // eslint-disable-next-line no-console
  console.log(
    `[StartupProfiler:${label}] ${event} +${deltaMs}ms (${Platform.OS})`,
  );
}

function mark(event: string, options?: StartupProfilerOptions) {
  const { enabled = __DEV__, label = DEFAULT_LABEL } = options ?? {};
  if (!enabled) {
    return;
  }
  logMetric(label, event, Date.now() - appStart);
}

/**
 * Hook to capture high-level startup milestones for profiling on-device.
 * Logs mount timing and time-to-interactions completion; additional milestones
 * can be recorded via the `markStartupEvent` helper.
 */
export function useStartupProfiler(options?: StartupProfilerOptions) {
  const { enabled = __DEV__, label = DEFAULT_LABEL } = options ?? {};

  useEffect(() => {
    if (!enabled) {
      return;
    }

    mark("mounted", { enabled, label });

    const handle = InteractionManager.runAfterInteractions(() => {
      mark("interactions-complete", { enabled, label });
    });

    return () => {
      handle.cancel();
    };
  }, [enabled, label]);

  const markEvent = useCallback(
    (event: string) => {
      mark(event, { enabled, label });
    },
    [enabled, label],
  );

  return markEvent;
}

/**
 * Imperative helper to mark significant milestones (e.g. cache hydration,
 * first network response) outside of React component lifecycle hooks.
 */
export function markStartupEvent(
  event: string,
  options?: StartupProfilerOptions,
) {
  mark(event, options);
}
