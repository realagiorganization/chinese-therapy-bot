import { useCallback, useMemo, useRef, useState } from "react";

import { transcribeAudio } from "../api/voice";

type TranscriptHandler = (text: string) => void;

const FALLBACK_MIME_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];

function selectPreferredMimeType(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const MediaRecorderCtor = (window as any).MediaRecorder as typeof MediaRecorder | undefined;
  if (!MediaRecorderCtor || typeof MediaRecorderCtor.isTypeSupported !== "function") {
    return undefined;
  }
  for (const mimeType of FALLBACK_MIME_TYPES) {
    if (MediaRecorderCtor.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }
  return undefined;
}

function stopMediaStream(stream?: MediaStream | null) {
  if (!stream) {
    return;
  }
  for (const track of stream.getTracks()) {
    try {
      track.stop();
    } catch {
      // Ignore track stop errors during cleanup.
    }
  }
}

export type ServerTranscriber = {
  supported: boolean;
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  start: (onTranscript: TranscriptHandler) => Promise<void>;
  stop: () => void;
  clearError: () => void;
};

export function useServerTranscriber(locale: string): ServerTranscriber {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const supported = useMemo(() => {
    if (typeof window === "undefined" || typeof navigator === "undefined") {
      return false;
    }
    const hasMediaRecorder = "MediaRecorder" in window;
    const hasMediaDevices = Boolean(navigator.mediaDevices?.getUserMedia);
    return hasMediaRecorder && hasMediaDevices;
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
  }, []);

  const start = useCallback(
    async (onTranscript: TranscriptHandler) => {
      if (!supported || isRecording || isTranscribing) {
        return;
      }
      setError(null);

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const preferred = selectPreferredMimeType();
        const recorder = preferred ? new MediaRecorder(stream, { mimeType: preferred }) : new MediaRecorder(stream);

        streamRef.current = stream;
        recorderRef.current = recorder;
        chunksRef.current = [];

        recorder.ondataavailable = (event: BlobEvent) => {
          if (event.data && event.data.size > 0) {
            chunksRef.current.push(event.data);
          }
        };

        recorder.onerror = (event: MediaRecorderErrorEvent) => {
          setError(event.error?.message ?? "录音发生错误，请稍后重试。");
          setIsRecording(false);
          recorderRef.current = null;
          stopMediaStream(streamRef.current);
          streamRef.current = null;
        };

        recorder.onstop = async () => {
          setIsRecording(false);
          recorderRef.current = null;
          stopMediaStream(streamRef.current);
          streamRef.current = null;

          const mimeType = chunksRef.current[0]?.type || recorder.mimeType || "audio/webm";
          const blob = new Blob(chunksRef.current, { type: mimeType });
          chunksRef.current = [];

          if (blob.size === 0) {
            setError("未捕获到有效语音，请重新尝试。");
            return;
          }

          setIsTranscribing(true);
          try {
            const response = await transcribeAudio(blob, locale);
            const normalized = response.text.trim();
            if (!normalized) {
              setError("未识别到语音内容，请重新尝试。");
            } else {
              onTranscript(normalized);
            }
          } catch (transcriptionError: any) {
            const message =
              transcriptionError instanceof Error ? transcriptionError.message : String(transcriptionError);
            setError(message || "语音识别失败，请稍后再试。");
          } finally {
            setIsTranscribing(false);
          }
        };

        recorder.start();
        setIsRecording(true);
      } catch (err: any) {
        setError(err?.message ?? "无法访问麦克风，请检查浏览器权限。");
        stopMediaStream(streamRef.current);
        streamRef.current = null;
        recorderRef.current = null;
        setIsRecording(false);
      }
    },
    [supported, isRecording, isTranscribing, locale]
  );

  return {
    supported,
    isRecording,
    isTranscribing,
    error,
    start,
    stop,
    clearError
  };
}
