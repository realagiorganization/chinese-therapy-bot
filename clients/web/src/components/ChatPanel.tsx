import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import type { ChatTemplate } from "../api/types";
import { Button, Card, Typography } from "../design-system";
import { useChatSession, type ChatTranscriptMessage } from "../hooks/useChatSession";
import { useServerTranscriber } from "../hooks/useServerTranscriber";
import { useChatTemplates } from "../hooks/useChatTemplates";

type SpeechRecognitionAlternativeLike = {
  transcript?: string;
};

type SpeechRecognitionResultLike = {
  readonly length: number;
  [index: number]: SpeechRecognitionAlternativeLike | undefined;
};

type SpeechRecognitionResultListLike = {
  readonly length: number;
  [index: number]: SpeechRecognitionResultLike | undefined;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: SpeechRecognitionResultListLike;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event?: unknown) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
};

type SpeechRecognitionConstructorLike = new () => SpeechRecognitionLike;

type SpeechRecognitionWindow = Window &
  typeof globalThis & {
    SpeechRecognition?: SpeechRecognitionConstructorLike;
    webkitSpeechRecognition?: SpeechRecognitionConstructorLike;
  };

function normalizeChatContent(raw: string): string {
  if (!raw) {
    return "";
  }

  let text = raw.replace(/\r\n?/g, "\n");

  // Remove fenced code block markers while keeping the content.
  text = text.replace(/```([\s\S]*?)```/g, (_, code) => code.trim());
  // Remove inline code markers.
  text = text.replace(/`([^`]*)`/g, "$1");
  // Unwrap markdown links and images, keeping the readable label.
  text = text.replace(/!\[([^\]]*)]\([^)]+\)/g, "$1");
  text = text.replace(/\[([^\]]+)]\([^)]+\)/g, "$1");
  // Drop emphasis markers.
  text = text.replace(/(\*\*|__)(.*?)\1/g, "$2");
  text = text.replace(/(\*|_)(.*?)\1/g, "$2");
  // Remove strikethrough markers.
  text = text.replace(/~~(.*?)~~/g, "$1");
  // Remove block quote indicators.
  text = text.replace(/^\s{0,3}>\s?/gm, "");
  // Remove heading markers.
  text = text.replace(/^\s{0,3}#{1,6}\s+/gm, "");
  // Replace ordered / unordered list markers with a plain bullet.
  text = text.replace(/^\s{0,3}(?:[-*+]|\d+\.)\s+/gm, "• ");
  // Unescape common escaped characters.
  text = text.replace(/\\([\\`*_{}[\]()#+\-.!])/g, "$1");
  // Collapse excessive blank lines.
  text = text.replace(/\n{3,}/g, "\n\n");

  return text.trim();
}

function scoreVoiceMatch(voice: SpeechSynthesisVoice, locale: string): number {
  const target = locale.toLowerCase();
  const base = target.split("-")[0] ?? target;
  const voiceLang = voice.lang?.toLowerCase() ?? "";
  const voiceName = voice.name?.toLowerCase() ?? "";

  let score = 0;

  if (voiceLang === target) {
    score += 6;
  } else if (voiceLang.startsWith(base)) {
    score += 4;
  } else if (voiceLang.includes(base)) {
    score += 2;
  }

  if (voiceName.includes("neural") || voiceName.includes("natural")) {
    score += 3;
  } else if (voiceName.includes("online") || voiceName.includes("cloud")) {
    score += 2;
  }

  if (!voice.localService) {
    score += 1;
  }

  if (voice.default) {
    score += 0.5;
  }

  return score;
}

function selectBestVoice(voices: SpeechSynthesisVoice[], locale: string): SpeechSynthesisVoice | null {
  if (voices.length === 0) {
    return null;
  }

  const scored = [...voices]
    .map((voice) => ({ voice, score: scoreVoiceMatch(voice, locale) }))
    .sort((a, b) => b.score - a.score);

  return scored[0]?.voice ?? voices[0] ?? null;
}

function getSpeechRecognitionCtor(): SpeechRecognitionConstructorLike | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const speechWindow = window as SpeechRecognitionWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

function useSpeechRecognition(locale: string) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const shouldListenRef = useRef(false);

  const supported = useMemo(() => {
    return Boolean(getSpeechRecognitionCtor());
  }, []);

  const start = useCallback(
    (onTranscript: (text: string) => void) => {
      if (!supported || isListening) {
        return;
      }
      const RecognitionCtor = getSpeechRecognitionCtor();
      if (!RecognitionCtor) {
        return;
      }

      try {
        const recognition = new RecognitionCtor();
        recognition.lang = locale;
        recognition.interimResults = false;
        recognition.continuous = true;

        recognition.onresult = (event: SpeechRecognitionEventLike) => {
          let transcript = "";
          for (let i = event.resultIndex; i < event.results.length; i += 1) {
            const result = event.results[i];
            if (!result) {
              continue;
            }
            const alternative = result[0];
            transcript += alternative?.transcript ?? "";
          }
          if (transcript.trim().length > 0) {
            onTranscript(transcript.trim());
          }
        };

        recognition.onerror = () => {
          shouldListenRef.current = false;
          setIsListening(false);
          recognition.stop();
        };

        recognition.onend = () => {
          if (!shouldListenRef.current) {
            setIsListening(false);
            if (recognitionRef.current === recognition) {
              recognitionRef.current = null;
            }
            return;
          }

          try {
            recognition.start();
          } catch (restartError) {
            console.warn("[Voice] Failed to restart speech recognition", restartError);
            shouldListenRef.current = false;
            setIsListening(false);
          }
        };

        recognitionRef.current = recognition;
        shouldListenRef.current = true;
        recognition.start();
        setIsListening(true);
      } catch (error) {
        console.warn("[Voice] Failed to start speech recognition", error);
        shouldListenRef.current = false;
        recognitionRef.current = null;
        setIsListening(false);
      }
    },
    [locale, isListening, supported]
  );

  const stop = useCallback(() => {
    shouldListenRef.current = false;
    try {
      recognitionRef.current?.stop();
    } catch {
      // ignored
    } finally {
      recognitionRef.current = null;
      setIsListening(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      shouldListenRef.current = false;
      try {
        recognitionRef.current?.abort?.();
        recognitionRef.current?.stop?.();
      } catch {
        // ignore abort errors on unmount
      }
    };
  }, []);

  return { supported, isListening, start, stop };
}

function useSpeechSynthesis(locale: string) {
  const supported = useMemo(
    () => typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window,
    []
  );
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const refreshVoice = useCallback(() => {
    if (!supported) {
      return;
    }
    const availableVoices = window.speechSynthesis.getVoices();
    if (!availableVoices || availableVoices.length === 0) {
      return;
    }
    const preferred = selectBestVoice(availableVoices, locale) ?? availableVoices[0] ?? null;
    if (!preferred) {
      return;
    }
    setVoice((current) => {
      if (current && current.voiceURI === preferred.voiceURI) {
        return current;
      }
      return preferred;
    });
  }, [locale, supported]);

  useEffect(() => {
    if (!supported) {
      return;
    }

    refreshVoice();

    const handleVoiceChange = () => {
      refreshVoice();
    };

    const synthesis = window.speechSynthesis;
    if ("addEventListener" in synthesis && typeof synthesis.addEventListener === "function") {
      synthesis.addEventListener("voiceschanged", handleVoiceChange);
      return () => {
        synthesis.removeEventListener("voiceschanged", handleVoiceChange);
      };
    }

    const previousHandler = synthesis.onvoiceschanged;
    synthesis.onvoiceschanged = handleVoiceChange;
    return () => {
      if (synthesis.onvoiceschanged === handleVoiceChange) {
        synthesis.onvoiceschanged = previousHandler ?? null;
      }
    };
  }, [supported, refreshVoice]);

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text) {
        return;
      }
      try {
        window.speechSynthesis.cancel();
        const cleanText = normalizeChatContent(text);
        if (!cleanText) {
          setIsSpeaking(false);
          return;
        }
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = locale;
        if (voice) {
          utterance.voice = voice;
        }
        // Slow down synthetic delivery slightly for a more natural cadence.
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 1;
        utterance.onstart = () => {
          setIsSpeaking(true);
        };
        const handleUtteranceDone = () => {
          setIsSpeaking(false);
          if (utteranceRef.current === utterance) {
            utteranceRef.current = null;
          }
        };
        utterance.onend = handleUtteranceDone;
        utterance.onerror = handleUtteranceDone;
        utterance.onpause = () => {
          setIsSpeaking(false);
        };
        utterance.onresume = () => {
          setIsSpeaking(true);
        };
        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      } catch (error) {
        console.warn("[Voice] Failed to speak text", error);
        setIsSpeaking(false);
      }
    },
    [locale, supported, voice]
  );

  const cancel = useCallback(() => {
    if (!supported) {
      return;
    }
    try {
      window.speechSynthesis.cancel();
    } catch {
      // ignore cancel issues
    } finally {
      utteranceRef.current = null;
      setIsSpeaking(false);
    }
  }, [supported]);

  useEffect(
    () => () => {
      cancel();
    },
    [cancel]
  );

  return { supported, speak, cancel, isSpeaking };
}

function renderTimestamp(date: string) {
  try {
    const parsed = new Date(date);
    return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

type ChatPanelProps = {
  className?: string;
};

export function ChatPanel({ className }: ChatPanelProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language ?? "zh-CN";
  const {
    messages,
    sendMessage,
    cancelStreaming,
    resetSession,
    isStreaming,
    error,
    clearError,
    recommendations,
    memoryHighlights,
    knowledgeSnippets,
    resolvedLocale
  } = useChatSession(locale);
  const sessionLocale = resolvedLocale || locale;
  const {
    status: templateStatus,
    templates: chatTemplates,
    topics: templateTopics,
    error: templateError,
    selectedTopic: selectedTemplateTopic,
    setSelectedTopic: setSelectedTemplateTopic,
    refetch: refetchTemplates
  } = useChatTemplates(sessionLocale);
  const {
    supported: serverVoiceSupported,
    isRecording: serverIsRecording,
    isTranscribing: serverIsTranscribing,
    error: serverVoiceError,
    start: startServerRecording,
    stop: stopServerRecording,
    clearError: clearServerError
  } = useServerTranscriber(sessionLocale);

  const [input, setInput] = useState("");
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [manualSpeakEnabled, setManualSpeakEnabled] = useState(false);
  const { supported: voiceSupported, isListening, start, stop } = useSpeechRecognition(sessionLocale);
  const {
    supported: speechSupported,
    speak,
    cancel,
    isSpeaking: speechInProgress
  } = useSpeechSynthesis(sessionLocale);
  const lastSpokenIdRef = useRef<string | null>(null);
  const transcriptContainerRef = useRef<HTMLDivElement | null>(null);
  const voiceError = useMemo(() => {
    if (error && serverVoiceError) {
      return `${error} • ${serverVoiceError}`;
    }
    return error ?? serverVoiceError;
  }, [error, serverVoiceError]);

  const templateTopicLabel = useCallback(
    (topic: string) => {
      const fallback = topic.replace(/[_-]/g, " ");
      const capitalized = fallback.replace(/\b\w/g, (character) => character.toUpperCase());
      return t(`chat.templates.topic.${topic}`, { defaultValue: capitalized });
    },
    [t]
  );

  const showTemplateSection =
    templateStatus !== "idle" || chatTemplates.length > 0 || Boolean(templateError);

  const handleTemplateFilter = useCallback(
    (topic: string | null) => {
      setSelectedTemplateTopic(topic);
    },
    [setSelectedTemplateTopic]
  );

  const handleTemplateApply = useCallback(
    (template: ChatTemplate) => {
      setInput((previous) => {
        if (!previous.trim()) {
          return template.userPrompt;
        }
        return `${previous.trim()}\n${template.userPrompt}`.trim();
      });
    },
    [setInput]
  );

  const handleTemplateRetry = useCallback(() => {
    refetchTemplates();
  }, [refetchTemplates]);

  useEffect(() => {
    const container = transcriptContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!speechSupported) {
      return;
    }
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && !message.streaming && message.content.trim().length > 0);
    if (!lastAssistant) {
      return;
    }
    if (!autoSpeak && !manualSpeakEnabled) {
      return;
    }
    if (lastSpokenIdRef.current === lastAssistant.id) {
      return;
    }
    lastSpokenIdRef.current = lastAssistant.id;
    speak(lastAssistant.content);
  }, [messages, autoSpeak, manualSpeakEnabled, speechSupported, speak]);

  useEffect(() => {
    if (!speechSupported && manualSpeakEnabled) {
      setManualSpeakEnabled(false);
      cancel();
    }
  }, [speechSupported, manualSpeakEnabled, cancel]);

  const handleSubmit = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      if (!input.trim()) {
        return;
      }
      await sendMessage(input);
      setInput("");
      if (isListening) {
        stop();
      }
      if (serverIsRecording) {
        stopServerRecording();
      }
    },
    [input, sendMessage, isListening, stop, serverIsRecording, stopServerRecording]
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        void handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleVoiceToggle = useCallback(() => {
    if (voiceSupported) {
      if (isListening) {
        stop();
      } else {
        start((transcript) => {
          setInput((prev) => {
            if (!prev) {
              return transcript;
            }
            return `${prev.trim()} ${transcript}`.trim();
          });
        });
      }
      return;
    }
    if (serverVoiceSupported) {
      if (serverIsRecording) {
        stopServerRecording();
      } else {
        void startServerRecording((transcript) => {
          setInput((prev) => {
            if (!prev) {
              return transcript;
            }
            return `${prev.trim()} ${transcript}`.trim();
          });
        });
      }
    }
  }, [
    voiceSupported,
    isListening,
    start,
    stop,
    serverVoiceSupported,
    serverIsRecording,
    stopServerRecording,
    startServerRecording
  ]);

  const handleAutoSpeakToggle = useCallback(() => {
    if (!speechSupported) {
      return;
    }
    if (manualSpeakEnabled) {
      setManualSpeakEnabled(false);
      cancel();
    }
    setAutoSpeak((prev) => {
      const next = !prev;
      if (!next) {
        cancel();
      }
      return next;
    });
  }, [speechSupported, cancel, manualSpeakEnabled]);

  const handlePlayLastReply = useCallback(() => {
    if (!speechSupported) {
      return;
    }
    if (manualSpeakEnabled) {
      setManualSpeakEnabled(false);
      cancel();
      return;
    }
    lastSpokenIdRef.current = null;
    setManualSpeakEnabled(true);
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && !message.streaming && message.content.trim().length > 0);
    if (lastAssistant) {
      lastSpokenIdRef.current = lastAssistant.id;
      speak(lastAssistant.content);
    }
  }, [messages, speechSupported, manualSpeakEnabled, cancel, speak]);

  const renderMessage = useCallback(
    (message: ChatTranscriptMessage) => {
      const isUser = message.role === "user";
      const alignment: "flex-end" | "flex-start" = isUser ? "flex-end" : "flex-start";
      const bubbleColor = isUser ? "var(--mw-color-primary)" : "rgba(148, 163, 184, 0.15)";
      const textColor = isUser ? "#FFFFFF" : "var(--text-primary)";
      const secondary = !isUser ? "var(--text-secondary)" : "rgba(255,255,255,0.75)";

      return (
        <div key={message.id} style={{ display: "flex", justifyContent: alignment }}>
          <div
            style={{
              display: "grid",
              gap: "6px",
              maxWidth: "75%",
              background: bubbleColor,
              color: textColor,
              borderRadius: "18px",
              padding: "12px 16px",
              boxShadow: isUser ? "none" : "var(--mw-shadow-sm)",
              border: isUser ? "none" : "1px solid rgba(148, 163, 184, 0.18)"
            }}
          >
            <Typography variant="body" style={{ whiteSpace: "pre-wrap", color: textColor }}>
              {message.content.trim().length > 0
                ? normalizeChatContent(message.content)
                : message.streaming
                  ? t("chat.generating")
                  : ""}
            </Typography>
            <Typography variant="caption" style={{ color: secondary, textAlign: isUser ? "right" : "left" }}>
              {message.streaming ? t("chat.streaming") : renderTimestamp(message.createdAt)}
            </Typography>
          </div>
        </div>
      );
    },
    [t]
  );

  const handleDismissError = useCallback(() => {
    if (error) {
      clearError();
    }
    if (serverVoiceError) {
      clearServerError();
    }
  }, [error, clearError, serverVoiceError, clearServerError]);

  return (
    <Card
      padding="lg"
      elevated
      className={className}
      style={{
        display: "grid",
        gap: "var(--mw-spacing-md)",
        background: "linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(226,232,240,0.35) 100%)"
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "var(--mw-spacing-sm)",
          flexWrap: "wrap"
        }}
      >
        <div style={{ display: "grid", gap: "4px" }}>
          <Typography variant="subtitle">{t("chat.title")}</Typography>
          <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
            {t("chat.subtitle")}
          </Typography>
        </div>
        <div style={{ display: "flex", gap: "var(--mw-spacing-xs)", flexWrap: "wrap" }}>
          <Button variant="ghost" size="sm" onClick={resetSession}>
            {t("chat.reset")}
          </Button>
          {isStreaming && (
            <Button variant="ghost" size="sm" onClick={cancelStreaming}>
              {t("chat.cancel_stream")}
            </Button>
          )}
        </div>
      </div>

      <div
        ref={transcriptContainerRef}
        style={{
          background: "rgba(255,255,255,0.7)",
          borderRadius: "var(--mw-radius-lg)",
          padding: "var(--mw-spacing-md)",
          border: "1px solid rgba(148, 163, 184, 0.25)",
          maxHeight: "360px",
          overflowY: "auto",
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        {messages.length === 0 ? (
          <Typography variant="body" style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            {t("chat.empty_state")}
          </Typography>
        ) : (
          messages.map(renderMessage)
        )}
      </div>

      {showTemplateSection && (
        <div
          style={{
            display: "grid",
            gap: "var(--mw-spacing-sm)",
            background: "rgba(226,232,240,0.35)",
            borderRadius: "var(--mw-radius-md)",
            border: "1px solid rgba(148,163,184,0.25)",
            padding: "var(--mw-spacing-md)"
          }}
        >
          <div style={{ display: "grid", gap: "2px" }}>
            <Typography variant="caption" style={{ fontWeight: 600, color: "var(--mw-color-primary)" }}>
              {t("chat.templates.heading")}
            </Typography>
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {t("chat.templates.subtitle")}
            </Typography>
          </div>

          <div
            style={{
              display: "flex",
              gap: "var(--mw-spacing-xs)",
              flexWrap: "wrap"
            }}
          >
            <Button
              type="button"
              variant={selectedTemplateTopic === null ? "secondary" : "ghost"}
              size="sm"
              onClick={() => handleTemplateFilter(null)}
            >
              {t("chat.templates.all")}
            </Button>
            {templateTopics.map((topic) => (
              <Button
                key={topic}
                type="button"
                variant={selectedTemplateTopic === topic ? "secondary" : "ghost"}
                size="sm"
                onClick={() => handleTemplateFilter(topic)}
              >
                {templateTopicLabel(topic)}
              </Button>
            ))}
          </div>

          {templateStatus === "loading" && chatTemplates.length === 0 && (
            <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
              {t("chat.templates.loading")}
            </Typography>
          )}

          {templateError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "var(--mw-spacing-sm)",
                background: "rgba(239,68,68,0.08)",
                borderRadius: "var(--mw-radius-sm)",
                border: "1px solid rgba(239,68,68,0.2)",
                padding: "var(--mw-spacing-xs) var(--mw-spacing-sm)"
              }}
            >
              <Typography variant="body" style={{ color: "var(--mw-color-danger)" }}>
                {t("chat.templates.error")} {templateError}
              </Typography>
              <Button type="button" variant="ghost" size="sm" onClick={handleTemplateRetry}>
                {t("chat.templates.retry")}
              </Button>
            </div>
          )}

          {chatTemplates.length > 0 && (
            <div
              style={{
                display: "grid",
                gap: "var(--mw-spacing-sm)"
              }}
            >
              {chatTemplates.map((template) => (
                <div
                  key={template.id}
                  style={{
                    display: "grid",
                    gap: "6px",
                    background: "#FFFFFF",
                    borderRadius: "var(--mw-radius-md)",
                    border: "1px solid rgba(148,163,184,0.25)",
                    padding: "var(--mw-spacing-sm)"
                  }}
                >
                  <Typography variant="body" style={{ fontWeight: 600 }}>
                    {template.title}
                  </Typography>

                  <div style={{ display: "grid", gap: "4px" }}>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {t("chat.templates.user_prompt_label")}
                    </Typography>
                    <Typography variant="body">{template.userPrompt}</Typography>
                  </div>

                  {template.assistantExample && (
                    <div style={{ display: "grid", gap: "4px" }}>
                      <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                        {t("chat.templates.assistant_example_label")}
                      </Typography>
                      <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                        {template.assistantExample}
                      </Typography>
                    </div>
                  )}

                  {template.followUpQuestions.length > 0 && (
                    <div style={{ display: "grid", gap: "4px" }}>
                      <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                        {t("chat.templates.follow_up_label")}
                      </Typography>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          color: "var(--text-secondary)",
                          fontSize: "0.9rem"
                        }}
                      >
                        {template.followUpQuestions.map((question) => (
                          <li key={question}>{question}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {template.selfCareTips.length > 0 && (
                    <div style={{ display: "grid", gap: "4px" }}>
                      <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                        {t("chat.templates.self_care_label")}
                      </Typography>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          color: "var(--text-secondary)",
                          fontSize: "0.9rem"
                        }}
                      >
                        {template.selfCareTips.map((tip) => (
                          <li key={tip}>{tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {template.keywords.length > 0 && (
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {t("chat.templates.keywords_label", {
                        keywords: template.keywords.join(" · ")
                      })}
                    </Typography>
                  )}

                  <div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => handleTemplateApply(template)}>
                      {t("chat.templates.use_prompt")}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {voiceError && (
        <div
          style={{
            background: "rgba(239,68,68,0.12)",
            borderRadius: "var(--mw-radius-md)",
            padding: "var(--mw-spacing-sm)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "var(--mw-spacing-sm)"
          }}
        >
          <Typography variant="body" style={{ color: "var(--mw-color-danger)" }}>
            {t("chat.error_prefix")} {voiceError}
          </Typography>
          <Button variant="ghost" size="sm" onClick={handleDismissError}>
            {t("chat.dismiss")}
          </Button>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        style={{
          display: "grid",
          gap: "var(--mw-spacing-sm)"
        }}
      >
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("chat.input_placeholder")}
          style={{
            width: "100%",
            minHeight: "96px",
            borderRadius: "var(--mw-radius-md)",
            border: "1px solid var(--mw-border-subtle)",
            padding: "12px 14px",
            fontSize: "1rem",
            fontFamily: "var(--mw-font-base)",
            resize: "vertical",
            background: "rgba(255,255,255,0.9)"
          }}
          disabled={isStreaming && !voiceSupported}
        />
        <div
          style={{
            display: "flex",
            gap: "var(--mw-spacing-sm)",
            flexWrap: "wrap",
            alignItems: "center"
          }}
        >
          <Button
            type="submit"
            disabled={!input.trim() && !isListening && !serverIsRecording && !serverIsTranscribing}
          >
            {isStreaming ? t("chat.sending") : t("chat.send")}
          </Button>
          {(voiceSupported || serverVoiceSupported) && (
            <Button
              type="button"
              variant="secondary"
              onClick={handleVoiceToggle}
              disabled={serverIsTranscribing}
            >
              {voiceSupported
                ? isListening
                  ? t("chat.stop_voice")
                  : t("chat.start_voice")
                : serverIsRecording
                  ? t("chat.stop_recording")
                  : serverIsTranscribing
                    ? t("chat.transcribing")
                    : t("chat.start_recording")}
            </Button>
          )}
          {speechSupported && (
            <>
              <Button type="button" variant="ghost" onClick={handleAutoSpeakToggle}>
                {autoSpeak ? t("chat.auto_speak_disable") : t("chat.auto_speak_enable")}
              </Button>
              <Button
                type="button"
                variant={manualSpeakEnabled ? "secondary" : "ghost"}
                onClick={handlePlayLastReply}
                aria-pressed={manualSpeakEnabled}
                aria-busy={manualSpeakEnabled && speechInProgress}
              >
                {manualSpeakEnabled ? t("chat.stop_speaking") : t("chat.speak_reply")}
              </Button>
            </>
          )}
        </div>
      </form>

      {(memoryHighlights.length > 0 || recommendations.length > 0 || knowledgeSnippets.length > 0) && (
        <div
          style={{
            display: "grid",
            gap: "var(--mw-spacing-sm)"
          }}
        >
          {memoryHighlights.length > 0 && (
            <div>
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {t("chat.memory_highlights")}
              </Typography>
              <div
                style={{
                  marginTop: "6px",
                  display: "grid",
                  gap: "var(--mw-spacing-xs)"
                }}
              >
                {memoryHighlights.map((highlight, index) => (
                  <div
                    key={`${highlight.summary}-${index}`}
                    style={{
                      background: "rgba(59,130,246,0.08)",
                      borderRadius: "var(--mw-radius-md)",
                      padding: "10px 12px",
                      border: "1px solid rgba(59,130,246,0.15)"
                    }}
                  >
                    <Typography variant="body">{highlight.summary}</Typography>
                    {highlight.keywords.length > 0 && (
                      <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                        {t("chat.keywords", { keywords: highlight.keywords.join(" / ") })}
                      </Typography>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {knowledgeSnippets.length > 0 && (
            <div>
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {t("chat.knowledge_snippets", { defaultValue: "心理教育提示" })}
              </Typography>
              <div
                style={{
                  marginTop: "6px",
                  display: "grid",
                  gap: "var(--mw-spacing-xs)"
                }}
              >
                {knowledgeSnippets.map((snippet) => (
                  <div
                    key={snippet.entryId}
                    style={{
                      borderRadius: "var(--mw-radius-md)",
                      border: "1px solid rgba(2,132,199,0.35)",
                      padding: "10px 12px",
                      background: "rgba(14,165,233,0.1)"
                    }}
                  >
                    <Typography variant="body" style={{ fontWeight: 600 }}>
                      {snippet.title}
                    </Typography>
                    <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                      {snippet.summary}
                    </Typography>
                    {snippet.guidance.slice(0, 2).map((line, index) => (
                      <Typography key={`${snippet.entryId}-${index}`} variant="caption">
                        {"• " + line}
                      </Typography>
                    ))}
                    {snippet.source && (
                      <Typography
                        variant="caption"
                        style={{ color: "var(--text-muted)", fontStyle: "italic" }}
                      >
                        {snippet.source}
                      </Typography>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {recommendations.length > 0 && (
            <div>
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {t("chat.recommendations")}
              </Typography>
              <div
                style={{
                  marginTop: "6px",
                  display: "grid",
                  gap: "var(--mw-spacing-xs)"
                }}
              >
                {recommendations.map((recommendation) => (
                  <div
                    key={recommendation.therapistId}
                    style={{
                      borderRadius: "var(--mw-radius-md)",
                      border: "1px solid rgba(148,163,184,0.3)",
                      padding: "10px 12px",
                      background: "#FFFFFF"
                    }}
                  >
                    <Typography variant="body" style={{ fontWeight: 600 }}>
                      {recommendation.name} · {recommendation.title}
                    </Typography>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {recommendation.specialties.slice(0, 3).join(" · ")}
                    </Typography>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {recommendation.reason}
                    </Typography>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
