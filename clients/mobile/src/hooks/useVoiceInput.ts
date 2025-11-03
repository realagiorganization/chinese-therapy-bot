import { useCallback, useMemo } from "react";

import {
  useLocalVoiceInput,
  type LocalVoiceInputController,
} from "./useLocalVoiceInput";
import {
  useRemoteVoiceInput,
  type TranscriptHandler,
  type VoiceInputController as RemoteVoiceInputController,
} from "./useRemoteVoiceInput";

export type VoiceInputMode = "remote" | "local";

export type VoiceInputController = {
  supported: boolean;
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  start: (onTranscript: TranscriptHandler) => Promise<void>;
  stop: () => Promise<void>;
  cancel: () => Promise<void>;
  clearError: () => void;
  mode: VoiceInputMode;
  remoteSupported: boolean;
  localSupported: boolean;
};

type UseVoiceInputOptions = {
  preferLocal?: boolean;
};

type ResolvedControllers = {
  remote: RemoteVoiceInputController;
  local: LocalVoiceInputController;
};

function resolveMode(
  controllers: ResolvedControllers,
  preferLocal: boolean,
): VoiceInputMode {
  if (preferLocal && controllers.local.supported) {
    return "local";
  }
  if (controllers.remote.supported) {
    return "remote";
  }
  return controllers.local.supported ? "local" : "remote";
}

export function useVoiceInput(
  locale: string,
  accessToken: string | null,
  options?: UseVoiceInputOptions,
): VoiceInputController {
  const remote = useRemoteVoiceInput(locale, accessToken);
  const local = useLocalVoiceInput(locale);

  const {
    supported: remoteSupported,
    isRecording: remoteRecording,
    isTranscribing: remoteTranscribing,
    error: remoteError,
    start: remoteStart,
    stop: remoteStop,
    cancel: remoteCancel,
    clearError: remoteClearError,
  } = remote;

  const {
    supported: localSupported,
    isRecording: localRecording,
    isProcessing: localProcessing,
    error: localError,
    start: localStart,
    stop: localStop,
    cancel: localCancel,
    clearError: localClearError,
  } = local;

  const preferLocal = options?.preferLocal ?? false;
  const mode = resolveMode({ remote, local }, preferLocal);

  const supported = mode === "local" ? localSupported : remoteSupported;
  const isRecording = mode === "local" ? localRecording : remoteRecording;
  const isTranscribing =
    mode === "local" ? localProcessing : remoteTranscribing;
  const error = mode === "local" ? localError : remoteError;
  const start = mode === "local" ? localStart : remoteStart;
  const stop = mode === "local" ? localStop : remoteStop;
  const cancel = mode === "local" ? localCancel : remoteCancel;

  const clearError = useCallback(() => {
    remoteClearError();
    localClearError();
  }, [remoteClearError, localClearError]);

  return useMemo(
    () => ({
      supported,
      isRecording,
      isTranscribing,
      error,
      start,
      stop,
      cancel,
      clearError,
      mode,
      remoteSupported,
      localSupported,
    }),
    [
      supported,
      isRecording,
      isTranscribing,
      error,
      start,
      stop,
      cancel,
      clearError,
      mode,
      remoteSupported,
      localSupported,
    ],
  );
}
