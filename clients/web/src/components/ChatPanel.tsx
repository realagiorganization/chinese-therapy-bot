import { FormEvent, KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Card, Typography } from "../design-system";
import { useChatSession, type ChatTranscriptMessage } from "../hooks/useChatSession";

function useSpeechRecognition(locale: string) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any | null>(null);

  const supported = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }, []);

  const start = useCallback(
    (onTranscript: (text: string) => void) => {
      if (!supported || isListening) {
        return;
      }
      const RecognitionCtor =
        typeof window !== "undefined"
          ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
          : null;
      if (!RecognitionCtor) {
        return;
      }

      try {
        const recognition = new RecognitionCtor();
        recognition.lang = locale;
        recognition.interimResults = false;

        recognition.onresult = (event: any) => {
          let transcript = "";
          for (let i = event.resultIndex; i < event.results.length; i += 1) {
            transcript += event.results[i][0]?.transcript ?? "";
          }
          if (transcript.trim().length > 0) {
            onTranscript(transcript.trim());
          }
        };

        recognition.onerror = () => {
          setIsListening(false);
          recognition.stop();
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
        setIsListening(true);
      } catch (error) {
        console.warn("[Voice] Failed to start speech recognition", error);
        setIsListening(false);
      }
    },
    [locale, isListening, supported]
  );

  const stop = useCallback(() => {
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

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text) {
        return;
      }
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = locale;
        window.speechSynthesis.speak(utterance);
      } catch (error) {
        console.warn("[Voice] Failed to speak text", error);
      }
    },
    [locale, supported]
  );

  const cancel = useCallback(() => {
    if (!supported) {
      return;
    }
    try {
      window.speechSynthesis.cancel();
    } catch {
      // ignore cancel issues
    }
  }, [supported]);

  useEffect(
    () => () => {
      cancel();
    },
    [cancel]
  );

  return { supported, speak, cancel };
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
    memoryHighlights
  } = useChatSession(locale);

  const [input, setInput] = useState("");
  const [autoSpeak, setAutoSpeak] = useState(false);
  const { supported: voiceSupported, isListening, start, stop } = useSpeechRecognition(locale);
  const { supported: speechSupported, speak, cancel } = useSpeechSynthesis(locale);
  const lastSpokenIdRef = useRef<string | null>(null);
  const transcriptContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = transcriptContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!autoSpeak || !speechSupported) {
      return;
    }
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && !message.streaming && message.content.trim().length > 0);
    if (!lastAssistant) {
      return;
    }
    if (lastSpokenIdRef.current === lastAssistant.id) {
      return;
    }
    lastSpokenIdRef.current = lastAssistant.id;
    speak(lastAssistant.content);
  }, [messages, autoSpeak, speechSupported, speak]);

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
    },
    [input, sendMessage, isListening, stop]
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
    if (!voiceSupported) {
      return;
    }
    if (isListening) {
      stop();
      return;
    }
    start((transcript) => {
      setInput((prev) => {
        if (!prev) {
          return transcript;
        }
        return `${prev.trim()} ${transcript}`.trim();
      });
    });
  }, [voiceSupported, isListening, start, stop]);

  const handleAutoSpeakToggle = useCallback(() => {
    if (!speechSupported) {
      return;
    }
    setAutoSpeak((prev) => {
      const next = !prev;
      if (!next) {
        cancel();
      }
      return next;
    });
  }, [speechSupported, cancel]);

  const handlePlayLastReply = useCallback(() => {
    if (!speechSupported) {
      return;
    }
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && !message.streaming && message.content.trim().length > 0);
    if (lastAssistant) {
      speak(lastAssistant.content);
    }
  }, [messages, speechSupported, speak]);

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
                ? message.content
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

      {error && (
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
            {t("chat.error_prefix")} {error}
          </Typography>
          <Button variant="ghost" size="sm" onClick={clearError}>
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
          <Button type="submit" disabled={!input.trim() && !isListening}>
            {isStreaming ? t("chat.sending") : t("chat.send")}
          </Button>
          {voiceSupported && (
            <Button type="button" variant="secondary" onClick={handleVoiceToggle}>
              {isListening ? t("chat.stop_voice") : t("chat.start_voice")}
            </Button>
          )}
          {speechSupported && (
            <>
              <Button type="button" variant="ghost" onClick={handleAutoSpeakToggle}>
                {autoSpeak ? t("chat.auto_speak_disable") : t("chat.auto_speak_enable")}
              </Button>
              <Button type="button" variant="ghost" onClick={handlePlayLastReply}>
                {t("chat.speak_reply")}
              </Button>
            </>
          )}
        </div>
      </form>

      {(memoryHighlights.length > 0 || recommendations.length > 0) && (
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
