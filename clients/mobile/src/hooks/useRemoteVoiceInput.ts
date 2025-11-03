import type { TranscriptionResponse } from "@services/voice";
import { transcribeRecording } from "@services/voice";
import { Audio, InterruptionModeAndroid, InterruptionModeIOS } from "expo-av";
import * as FileSystem from "expo-file-system";
import { useCallback, useMemo, useRef, useState } from "react";
import { Platform } from "react-native";

export type TranscriptHandler = (text: string) => void;

export type VoiceInputController = {
  supported: boolean;
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  start: (onTranscript: TranscriptHandler) => Promise<void>;
  stop: () => Promise<void>;
  cancel: () => Promise<void>;
  clearError: () => void;
};

const RECORDING_PRESET =
  Platform.OS === "android"
    ? Audio.RecordingOptionsPresets.LOW_QUALITY
    : Audio.RecordingOptionsPresets.HIGH_QUALITY;

async function ensureAudioPermission(): Promise<boolean> {
  const current = await Audio.getPermissionsAsync();
  if (current.granted) {
    return true;
  }
  if (!current.canAskAgain) {
    return false;
  }
  const updated = await Audio.requestPermissionsAsync();
  return updated.granted;
}

async function recordingUriToBlob(uri: string): Promise<Blob> {
  const response = await fetch(uri);
  return await response.blob();
}

async function cleanupRecordingFile(uri: string | null | undefined) {
  if (!uri) {
    return;
  }
  try {
    await FileSystem.deleteAsync(uri, { idempotent: true });
  } catch {
    // Ignore cleanup errors – file removal is best-effort.
  }
}

async function configureAudioForRecording() {
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
    staysActiveInBackground: false,
    interruptionModeIOS: InterruptionModeIOS.DoNotMix,
    shouldDuckAndroid: true,
    interruptionModeAndroid: InterruptionModeAndroid.DoNotMix,
    playThroughEarpieceAndroid: false,
  });
}

async function resetAudioMode() {
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: false,
    playsInSilentModeIOS: true,
    staysActiveInBackground: false,
    interruptionModeIOS: InterruptionModeIOS.DoNotMix,
    shouldDuckAndroid: true,
    interruptionModeAndroid: InterruptionModeAndroid.DoNotMix,
    playThroughEarpieceAndroid: false,
  });
}

export function useRemoteVoiceInput(
  locale: string,
  accessToken: string | null,
): VoiceInputController {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const transcriptHandlerRef = useRef<TranscriptHandler | null>(null);
  const pendingCleanupUriRef = useRef<string | null>(null);

  const supported = useMemo(() => Platform.OS !== "web", []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const start = useCallback(
    async (handler: TranscriptHandler) => {
      if (!supported || isRecording || isTranscribing) {
        return;
      }
      setError(null);

      if (!accessToken) {
        setError("未检测到登录信息，无法发送语音。");
        return;
      }

      const granted = await ensureAudioPermission();
      if (!granted) {
        setError("请在设置中授予麦克风权限。");
        return;
      }

      try {
        await configureAudioForRecording();
        const recording = new Audio.Recording();
        await recording.prepareToRecordAsync(RECORDING_PRESET);
        await recording.startAsync();

        recordingRef.current = recording;
        transcriptHandlerRef.current = handler;
        setIsRecording(true);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message || "无法开始录音，请重试。");
        try {
          await resetAudioMode();
        } catch {
          // ignore reset errors when failing to start recording
        }
        recordingRef.current = null;
        transcriptHandlerRef.current = null;
      }
    },
    [supported, isRecording, isTranscribing, accessToken],
  );

  const performTranscription = useCallback(
    async (uri: string | null): Promise<TranscriptionResponse | null> => {
      if (!uri || !accessToken) {
        return null;
      }
      try {
        const blob = await recordingUriToBlob(uri);
        setIsTranscribing(true);
        const result = await transcribeRecording(
          {
            blob,
            locale,
            accessToken,
          },
          Platform.OS,
        );
        return result;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message || "语音识别失败，请稍后再试。");
        return null;
      } finally {
        setIsTranscribing(false);
      }
    },
    [accessToken, locale],
  );

  const stop = useCallback(async () => {
    if (!recordingRef.current) {
      return;
    }
    const recording = recordingRef.current;
    recordingRef.current = null;
    setIsRecording(false);

    try {
      await recording.stopAndUnloadAsync();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "停止录音时发生错误。");
    }

    const uri = recording.getURI();
    pendingCleanupUriRef.current = uri ?? null;
    await resetAudioMode();

    const result = await performTranscription(uri ?? null);
    if (result) {
      const normalized = result.text.trim();
      if (normalized.length === 0) {
        setError("未识别到语音内容，请重新尝试。");
      } else if (transcriptHandlerRef.current) {
        transcriptHandlerRef.current(normalized);
      }
    }

    if (pendingCleanupUriRef.current) {
      await cleanupRecordingFile(pendingCleanupUriRef.current);
      pendingCleanupUriRef.current = null;
    }
    transcriptHandlerRef.current = null;
  }, [performTranscription]);

  const cancel = useCallback(async () => {
    if (!recordingRef.current) {
      return;
    }

    const recording = recordingRef.current;
    recordingRef.current = null;
    transcriptHandlerRef.current = null;
    setIsRecording(false);

    try {
      await recording.stopAndUnloadAsync();
    } catch {
      // Ignore stop errors when cancelling.
    }

    await resetAudioMode();
    const uri = recording.getURI();
    if (uri) {
      await cleanupRecordingFile(uri);
    }
  }, []);

  return {
    supported,
    isRecording,
    isTranscribing,
    error,
    start,
    stop,
    cancel,
    clearError,
  };
}
