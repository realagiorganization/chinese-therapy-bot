import Voice, {
  SpeechErrorEvent,
  SpeechResultsEvent,
} from "@react-native-voice/voice";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Platform } from "react-native";

type TranscriptHandler = (text: string) => void;

export type LocalVoiceInputController = {
  supported: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  start: (onTranscript: TranscriptHandler) => Promise<void>;
  stop: () => Promise<void>;
  cancel: () => Promise<void>;
  clearError: () => void;
};

const NOOP = () => undefined;

function normalizeTranscript(event: SpeechResultsEvent): string | null {
  const candidates = Array.isArray(event.value) ? event.value : [];
  for (const entry of candidates) {
    if (typeof entry === "string") {
      const trimmed = entry.trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }
  return null;
}

export function useLocalVoiceInput(locale: string): LocalVoiceInputController {
  const [supported, setSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const transcriptHandlerRef = useRef<TranscriptHandler | null>(null);
  const lastPartialRef = useRef<string | null>(null);

  const platformSupportsVoice = useMemo(() => Platform.OS !== "web", []);

  useEffect(() => {
    let cancelled = false;
    if (!platformSupportsVoice) {
      return;
    }

    Voice.isAvailable()
      .then((available) => {
        if (!cancelled) {
          setSupported(Boolean(available));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSupported(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [platformSupportsVoice]);

  useEffect(() => {
    if (!platformSupportsVoice) {
      return;
    }

    Voice.onSpeechStart = () => {
      setError(null);
      setIsRecording(true);
      setIsProcessing(false);
      lastPartialRef.current = null;
    };

    Voice.onSpeechResults = (event: SpeechResultsEvent) => {
      const transcript = normalizeTranscript(event);
      if (!transcript) {
        setError("未识别到语音内容，请重新尝试。");
        setIsProcessing(false);
        return;
      }
      lastPartialRef.current = transcript;
      if (transcriptHandlerRef.current) {
        transcriptHandlerRef.current(transcript);
        transcriptHandlerRef.current = null;
      }
      lastPartialRef.current = null;
      setIsProcessing(false);
    };

    Voice.onSpeechPartialResults = (event: SpeechResultsEvent) => {
      const transcript = normalizeTranscript(event);
      if (transcript) {
        lastPartialRef.current = transcript;
      }
    };

    Voice.onSpeechEnd = () => {
      setIsRecording(false);
      if (transcriptHandlerRef.current && lastPartialRef.current) {
        transcriptHandlerRef.current(lastPartialRef.current);
      }
      transcriptHandlerRef.current = null;
      lastPartialRef.current = null;
      setIsProcessing(false);
    };

    Voice.onSpeechError = (event: SpeechErrorEvent) => {
      const message = event.error?.message ?? "语音识别失败，请稍后再试。";
      setError(message);
      setIsRecording(false);
      setIsProcessing(false);
      transcriptHandlerRef.current = null;
      lastPartialRef.current = null;
    };

    Voice.onSpeechRecognized = NOOP;
    Voice.onSpeechVolumeChanged = NOOP;

    return () => {
      Voice.onSpeechStart = NOOP;
      Voice.onSpeechResults = NOOP;
      Voice.onSpeechPartialResults = NOOP;
      Voice.onSpeechEnd = NOOP;
      Voice.onSpeechError = NOOP;
      Voice.onSpeechRecognized = NOOP;
      Voice.onSpeechVolumeChanged = NOOP;
      Voice.destroy().catch(() => {});
    };
  }, [platformSupportsVoice]);

  const start = useCallback(
    async (handler: TranscriptHandler) => {
      if (!supported || isRecording) {
        return;
      }

      setError(null);
      transcriptHandlerRef.current = handler;
      lastPartialRef.current = null;

      try {
        setIsProcessing(false);
        await Voice.start(locale);
        setIsRecording(true);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message || "无法开始语音识别，请稍后再试。");
        transcriptHandlerRef.current = null;
        setIsRecording(false);
      }
    },
    [supported, isRecording, locale],
  );

  const stop = useCallback(async () => {
    if (!supported) {
      return;
    }

    if (!isRecording) {
      return;
    }

    setIsProcessing(true);
    try {
      await Voice.stop();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "停止语音识别时发生错误。");
      setIsProcessing(false);
    }
  }, [supported, isRecording]);

  const cancel = useCallback(async () => {
    if (!supported) {
      return;
    }

    transcriptHandlerRef.current = null;
    lastPartialRef.current = null;
    setIsRecording(false);
    setIsProcessing(false);
    setError(null);

    try {
      await Voice.cancel();
    } catch {
      // Ignore cancels that fail.
    }
  }, [supported]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    supported,
    isRecording,
    isProcessing,
    error,
    start,
    stop,
    cancel,
    clearError,
  };
}
