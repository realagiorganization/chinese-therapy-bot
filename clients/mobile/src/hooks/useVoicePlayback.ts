import { useVoiceSettings } from "@context/VoiceSettingsContext";
import * as Speech from "expo-speech";
import { useCallback, useEffect, useRef, useState } from "react";

function segmentText(text: string): string[] {
  if (!text) {
    return [];
  }

  const normalized = text
    .replace(/\r\n|\r|\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const segments: string[] = [];
  const sentenceRegex = /[^。！？!?．.]+[。！？!?．.]?|[。！？!?．.]/gu;

  for (const line of normalized) {
    const matches = line.match(sentenceRegex);
    if (!matches) {
      segments.push(line);
      continue;
    }
    for (const match of matches) {
      const trimmed = match.trim();
      if (trimmed.length > 0) {
        segments.push(trimmed);
      }
    }
  }

  return segments;
}

type SpeakOptions = {
  text: string;
  locale?: string;
};

export function useVoicePlayback() {
  const { enabled, rate, pitch } = useVoiceSettings();
  const queueRef = useRef<string[]>([]);
  const localeRef = useRef<string>("zh-CN");
  const [speaking, setSpeaking] = useState<boolean>(false);

  const stop = useCallback(() => {
    queueRef.current = [];
    setSpeaking(false);
    Speech.stop();
  }, []);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      setSpeaking(false);
      return;
    }
    const next = queueRef.current.shift();
    if (!next) {
      setSpeaking(false);
      return;
    }
    Speech.speak(next, {
      language: localeRef.current,
      rate,
      pitch,
      onDone: playNext,
      onStopped: stop,
      onError: stop,
    });
  }, [pitch, rate, stop]);

  const speak = useCallback(
    ({ text, locale }: SpeakOptions) => {
      if (!enabled) {
        return;
      }

      const segments = segmentText(text);
      if (segments.length === 0) {
        return;
      }

      Speech.stop();
      queueRef.current = segments;
      localeRef.current = locale ?? localeRef.current ?? "zh-CN";
      setSpeaking(true);
      playNext();
    },
    [enabled, playNext],
  );

  useEffect(() => {
    if (!enabled) {
      stop();
    }
  }, [enabled, stop]);

  useEffect(() => () => stop(), [stop]);

  return {
    speak,
    stop,
    speaking,
    enabled,
    rate,
    pitch,
  };
}
