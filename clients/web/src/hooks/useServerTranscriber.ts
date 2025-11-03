import { useCallback, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { transcribeAudio } from "../api/voice";

type TranscriptHandler = (text: string) => void;

const FALLBACK_MIME_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];

type MediaRecorderWindow = Window &
  typeof globalThis & {
    MediaRecorder?: typeof MediaRecorder;
  };

function getMediaRecorderCtor(): typeof MediaRecorder | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const mediaWindow = window as MediaRecorderWindow;
  return typeof mediaWindow.MediaRecorder === "function" ? mediaWindow.MediaRecorder : undefined;
}

function selectPreferredMimeType(): string | undefined {
  const MediaRecorderCtor = getMediaRecorderCtor();
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
  const { t } = useTranslation();

  const supported = useMemo(() => {
    if (typeof window === "undefined" || typeof navigator === "undefined") {
      return false;
    }
    const hasMediaRecorder = Boolean(getMediaRecorderCtor());
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
        const MediaRecorderCtor = getMediaRecorderCtor();
        if (!MediaRecorderCtor) {
          throw new Error(t("chat.voice_errors.unsupported"));
        }
        const recorder = preferred
          ? new MediaRecorderCtor(stream, { mimeType: preferred })
          : new MediaRecorderCtor(stream);

        streamRef.current = stream;
        recorderRef.current = recorder;
        chunksRef.current = [];

        recorder.ondataavailable = (event: BlobEvent) => {
          if (event.data && event.data.size > 0) {
            chunksRef.current.push(event.data);
          }
        };

        recorder.onerror = (event: Event & { error?: DOMException }) => {
          console.warn("[Voice] MediaRecorder error", event.error);
          setError(t("chat.voice_errors.recording_error"));
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
            setError(t("chat.voice_errors.no_audio"));
            return;
          }

          setIsTranscribing(true);
          try {
            const response = await transcribeAudio(blob, locale);
            const normalized = response.text.trim();
            if (!normalized) {
              setError(t("chat.voice_errors.no_transcript"));
            } else {
              onTranscript(normalized);
            }
          } catch (transcriptionError: unknown) {
            const message =
              transcriptionError instanceof Error ? transcriptionError.message : String(transcriptionError);
            console.warn("[Voice] Server transcription error", transcriptionError);
            setError(message || t("chat.voice_errors.transcription_failed"));
          } finally {
            setIsTranscribing(false);
          }
        };

        recorder.start();
        setIsRecording(true);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        const fallbackKey =
          err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "SecurityError")
            ? "chat.voice_errors.microphone_denied"
            : "chat.voice_errors.recording_error";
        console.warn("[Voice] Failed to start recording", err);
        setError(message || t(fallbackKey));
        stopMediaStream(streamRef.current);
        streamRef.current = null;
        recorderRef.current = null;
        setIsRecording(false);
      }
    },
    [supported, isRecording, isTranscribing, locale, t]
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
