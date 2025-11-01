import { useAuth } from "@context/AuthContext";
import { markStartupEvent } from "@hooks/useStartupProfiler";
import { useVoiceInput } from "@hooks/useVoiceInput";
import { sendMessage } from "@services/chat";
import { loadChatState, persistChatState } from "@services/chatCache";
import { useTheme } from "@theme/ThemeProvider";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { ChatMessage } from "../types/chat";
import type { TherapistRecommendation } from "../types/therapists";
type MessageWithId = ChatMessage & { id: string };

function Bubble({ message }: { message: MessageWithId }) {
  const theme = useTheme();
  const isUser = message.role === "user";
  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          alignSelf: isUser ? "flex-end" : "flex-start",
          backgroundColor: isUser
            ? theme.colors.primary
            : theme.colors.surfaceMuted,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          borderRadius: theme.radius.lg,
          marginVertical: theme.spacing.xs,
          maxWidth: "80%",
        },
        text: {
          color: isUser ? "#fff" : theme.colors.textPrimary,
          fontSize: 16,
          lineHeight: 22,
        },
        timestamp: {
          color: isUser ? "rgba(255,255,255,0.7)" : theme.colors.textSecondary,
          fontSize: 12,
          marginTop: 4,
        },
      }),
    [isUser, theme],
  );

  const timeLabel = useMemo(() => {
    try {
      const date = new Date(message.createdAt);
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }, [message.createdAt]);

  return (
    <View style={styles.container}>
      <Text style={styles.text}>{message.content}</Text>
      {timeLabel && <Text style={styles.timestamp}>{timeLabel}</Text>}
    </View>
  );
}

function RecommendationCard({
  recommendation,
}: {
  recommendation: TherapistRecommendation;
}) {
  const theme = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
        },
        title: {
          fontSize: 16,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        subtitle: {
          fontSize: 14,
          color: theme.colors.textSecondary,
        },
        tagList: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        },
        tag: {
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          color: theme.colors.primary,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.75,
          fontSize: 12,
        },
      }),
    [theme],
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{recommendation.name}</Text>
      <Text style={styles.subtitle}>{recommendation.summary}</Text>
      <View style={styles.tagList}>
        {recommendation.expertise.map((area) => (
          <Text key={area} style={styles.tag}>
            {area}
          </Text>
        ))}
      </View>
    </View>
  );
}

function resolveVoiceStatusLabel(
  isRecording: boolean,
  isTranscribing: boolean,
): string {
  if (isTranscribing) {
    return "语音识别中…";
  }
  if (isRecording) {
    return "保持按住录音";
  }
  return "长按说话";
}

export function ChatScreen() {
  const theme = useTheme();
  const { tokens, userId, logout } = useAuth();
  const cacheMarkedRef = useRef(false);
  const screenVisibleRef = useRef(false);
  const firstResponseRef = useRef(false);
  const listRef = useRef<FlatList<MessageWithId>>(null);
  const insets = useSafeAreaInsets();
  const [activeLocale, setActiveLocale] = useState("zh-CN");
  const {
    supported: voiceSupported,
    isRecording: isVoiceRecording,
    isTranscribing: isVoiceTranscribing,
    error: voiceError,
    start: startVoiceInput,
    stop: stopVoiceInput,
    cancel: cancelVoiceInput,
    clearError: clearVoiceError,
  } = useVoiceInput(activeLocale, tokens?.accessToken ?? null);
  const [messages, setMessages] = useState<MessageWithId[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [inputValue, setInputValue] = useState("");
  const [isSending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<
    TherapistRecommendation[]
  >([]);
  const [memoryHighlights, setMemoryHighlights] = useState<
    { summary: string; keywords: string[] }[]
  >([]);
  const [isRestoring, setRestoring] = useState<boolean>(true);
  const composerPadding = useMemo(
    () => Math.max(insets.bottom, theme.spacing.sm),
    [insets.bottom, theme.spacing.sm],
  );
  const keyboardVerticalOffset =
    Platform.OS === "ios" ? insets.top + theme.spacing.lg : 0;

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: theme.colors.surfaceBackground,
        },
        content: {
          flexGrow: 1,
          padding: theme.spacing.md,
        },
        composer: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          borderTopWidth: 1,
          borderColor: theme.colors.surfaceMuted,
          backgroundColor: theme.colors.surfaceCard,
        },
        input: {
          flex: 1,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.md,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          fontSize: 16,
        },
        sendButton: {
          backgroundColor: theme.colors.primary,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          borderRadius: theme.radius.md,
        },
        sendLabel: {
          color: "#fff",
          fontWeight: "600",
        },
        section: {
          gap: theme.spacing.sm,
          marginTop: theme.spacing.md,
        },
        sectionTitle: {
          fontSize: 18,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        highlight: {
          borderRadius: theme.radius.md,
          backgroundColor: "rgba(37, 99, 235, 0.05)",
          padding: theme.spacing.md,
        },
        highlightTitle: {
          fontWeight: "600",
          color: theme.colors.textPrimary,
          marginBottom: theme.spacing.xs,
        },
        highlightKeywords: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        header: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          borderBottomWidth: 1,
          borderColor: theme.colors.surfaceMuted,
          backgroundColor: theme.colors.surfaceCard,
        },
        headerTitle: {
          fontSize: 20,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        logoutButton: {
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
        },
        logoutLabel: {
          color: theme.colors.primary,
          fontWeight: "500",
        },
        errorText: {
          color: theme.colors.danger,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs,
        },
        restoringContainer: {
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          padding: theme.spacing.lg,
        },
        voiceButton: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          backgroundColor: theme.colors.surfaceCard,
        },
        voiceContainer: {
          alignItems: "center",
          justifyContent: "center",
          marginRight: theme.spacing.sm,
        },
        voiceButtonActive: {
          backgroundColor: theme.colors.primary,
          borderColor: theme.colors.primary,
        },
        voiceButtonDisabled: {
          opacity: 0.4,
        },
        voiceButtonLabel: {
          color: theme.colors.textPrimary,
          fontWeight: "600",
        },
        voiceButtonLabelActive: {
          color: "#fff",
        },
        voiceStatusText: {
          color: theme.colors.textSecondary,
          fontSize: 12,
          marginTop: theme.spacing.xs * 0.5,
        },
        voiceErrorText: {
          color: theme.colors.danger,
          fontSize: 12,
          paddingHorizontal: theme.spacing.md,
          paddingBottom: theme.spacing.xs,
        },
        voiceStatusRow: {
          flexDirection: "row",
          alignItems: "center",
          marginTop: theme.spacing.xs * 0.5,
        },
      }),
    [theme],
  );

  const scrollToLatestMessage = useCallback((animated: boolean) => {
    requestAnimationFrame(() => {
      listRef.current?.scrollToEnd({ animated });
    });
  }, []);

  const appendMessage = useCallback(
    (message: MessageWithId) => {
      setMessages((prev) => {
        const next = [...prev, message];
        scrollToLatestMessage(true);
        return next;
      });
    },
    [scrollToLatestMessage],
  );

  useEffect(() => {
    return () => {
      cancelVoiceInput().catch((error) => {
        console.warn("Failed to cancel voice input during cleanup", error);
      });
    };
  }, [cancelVoiceInput]);

  useEffect(() => {
    if (!userId) {
      setRestoring(false);
      return;
    }

    let isMounted = true;
    const hydrate = async () => {
      const cached = await loadChatState(userId);
      if (!isMounted) {
        return;
      }
      if (cached) {
        setMessages(cached.messages as MessageWithId[]);
        setSessionId(cached.sessionId);
        setRecommendations(cached.recommendations);
        setMemoryHighlights(cached.memoryHighlights);
        scrollToLatestMessage(false);
        if (cached.locale) {
          setActiveLocale(cached.locale);
        }
      }
      setRestoring(false);
    };

    setRestoring(true);
    hydrate().catch((error) => {
      console.warn("Failed to hydrate cached chat state", error);
      setRestoring(false);
    });

    return () => {
      isMounted = false;
    };
  }, [userId]);

  useEffect(() => {
    if (!userId || isRestoring) {
      return;
    }
    if (!cacheMarkedRef.current) {
      markStartupEvent("chat-cache-ready");
      cacheMarkedRef.current = true;
    }
    persistChatState(userId, {
      sessionId,
      messages,
      recommendations,
      memoryHighlights,
      locale: activeLocale,
    }).catch((error) => {
      console.warn("Failed to persist chat state", error);
    });
  }, [
    userId,
    sessionId,
    messages,
    recommendations,
    memoryHighlights,
    isRestoring,
    activeLocale,
  ]);

  useEffect(() => {
    if (!isRestoring && !screenVisibleRef.current) {
      markStartupEvent("chat-screen-visible");
      screenVisibleRef.current = true;
    }
  }, [isRestoring]);

  const handleInputChange = useCallback(
    (value: string) => {
      clearVoiceError();
      setInputValue(value);
    },
    [clearVoiceError],
  );

  const handleVoiceTranscript = useCallback(
    (transcript: string) => {
      clearVoiceError();
      setInputValue((prev) => {
        const normalized = prev.trimEnd();
        if (normalized.length === 0) {
          return transcript;
        }
        const spacer =
          normalized.endsWith("，") || normalized.endsWith("。") ? "" : " ";
        return `${normalized}${spacer}${transcript}`;
      });
    },
    [clearVoiceError],
  );

  const handleVoiceStart = useCallback(() => {
    clearVoiceError();
    startVoiceInput(handleVoiceTranscript).catch((error) => {
      console.warn("Failed to start voice input", error);
    });
  }, [clearVoiceError, startVoiceInput, handleVoiceTranscript]);

  const handleVoiceStop = useCallback(() => {
    stopVoiceInput().catch((error) => {
      console.warn("Failed to stop voice input", error);
    });
  }, [stopVoiceInput]);

  const handleVoiceCancel = useCallback(() => {
    cancelVoiceInput().catch((error) => {
      console.warn("Failed to cancel voice input", error);
    });
  }, [cancelVoiceInput]);

  const handleSend = useCallback(async () => {
    if (!tokens || !userId || inputValue.trim().length === 0) {
      return;
    }
    const userMessage: MessageWithId = {
      id: `${Date.now()}-user`,
      role: "user",
      content: inputValue.trim(),
      createdAt: new Date().toISOString(),
    };
    appendMessage(userMessage);
    setInputValue("");
    setSending(true);
    setError(null);
    try {
      const response = await sendMessage({
        accessToken: tokens.accessToken,
        userId,
        sessionId,
        message: userMessage.content,
        locale: activeLocale,
      });
      setSessionId(response.sessionId);
      const assistantMessage: MessageWithId = {
        id: `${Date.now()}-assistant`,
        role: response.reply.role,
        content: response.reply.content,
        createdAt: response.reply.createdAt,
      };
      appendMessage(assistantMessage);
      setRecommendations(response.recommendations);
      setMemoryHighlights(response.memoryHighlights);
      if (response.resolvedLocale) {
        setActiveLocale(response.resolvedLocale);
      }
      if (!firstResponseRef.current) {
        markStartupEvent("chat-first-response");
        firstResponseRef.current = true;
      }
    } catch (err) {
      console.warn("Failed to send chat message", err);
      setError(
        err instanceof Error ? err.message : "发送消息失败，请稍后重试。",
      );
    } finally {
      setSending(false);
    }
  }, [tokens, userId, inputValue, sessionId, activeLocale]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={keyboardVerticalOffset}
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MindWell 对话</Text>
        <Pressable onPress={logout} style={styles.logoutButton}>
          <Text style={styles.logoutLabel}>退出</Text>
        </Pressable>
      </View>

      {error && <Text style={styles.errorText}>{error}</Text>}

      {isRestoring ? (
        <View style={styles.restoringContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <Text
            style={{
              marginTop: theme.spacing.sm,
              color: theme.colors.textSecondary,
            }}
          >
            正在恢复会话…
          </Text>
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <Bubble message={item} />}
          contentContainerStyle={[
            styles.content,
            { paddingBottom: composerPadding + theme.spacing.lg },
          ]}
          keyboardShouldPersistTaps="handled"
          contentInset={{ bottom: composerPadding }}
          scrollIndicatorInsets={{ bottom: composerPadding }}
          initialNumToRender={12}
          onContentSizeChange={() => scrollToLatestMessage(false)}
        />
      )}

      <View style={{ paddingHorizontal: theme.spacing.md }}>
        {recommendations.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>推荐治疗师</Text>
            {recommendations.map((recommendation) => (
              <RecommendationCard
                key={recommendation.id}
                recommendation={recommendation}
              />
            ))}
          </View>
        )}

        {memoryHighlights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>疗程亮点</Text>
            {memoryHighlights.map((memory) => (
              <View key={memory.summary} style={styles.highlight}>
                <Text style={styles.highlightTitle}>{memory.summary}</Text>
                <Text style={styles.highlightKeywords}>
                  {memory.keywords.join(" · ")}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      <View
        style={[
          styles.composer,
          { paddingBottom: composerPadding, paddingTop: theme.spacing.sm },
        ]}
      >
        {voiceSupported && (
          <View style={styles.voiceContainer}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="按住进行语音输入"
              onPressIn={handleVoiceStart}
              onPressOut={handleVoiceStop}
              onTouchCancel={handleVoiceCancel}
              disabled={isSending || isVoiceTranscribing}
              style={[
                styles.voiceButton,
                isVoiceRecording && styles.voiceButtonActive,
                (isSending || isVoiceTranscribing) &&
                  styles.voiceButtonDisabled,
              ]}
            >
              <Text
                style={[
                  styles.voiceButtonLabel,
                  isVoiceRecording && styles.voiceButtonLabelActive,
                ]}
              >
                {isVoiceRecording ? "松开结束" : "按住语音"}
              </Text>
            </Pressable>
            <View style={styles.voiceStatusRow}>
              {isVoiceTranscribing && (
                <ActivityIndicator size="small" color={theme.colors.primary} />
              )}
              <Text
                style={[
                  styles.voiceStatusText,
                  isVoiceTranscribing && { marginLeft: theme.spacing.xs * 0.5 },
                ]}
              >
                {resolveVoiceStatusLabel(isVoiceRecording, isVoiceTranscribing)}
              </Text>
            </View>
          </View>
        )}

        <TextInput
          placeholder="说点什么..."
          value={inputValue}
          onChangeText={handleInputChange}
          style={styles.input}
          editable={!isSending && !isVoiceRecording && !isVoiceTranscribing}
        />
        <Pressable
          onPress={handleSend}
          style={[styles.sendButton, { opacity: inputValue.trim() ? 1 : 0.5 }]}
          disabled={inputValue.trim().length === 0 || isSending}
        >
          <Text style={styles.sendLabel}>{isSending ? "发送中…" : "发送"}</Text>
        </Pressable>
      </View>
      {voiceError && (
        <Text
          style={[
            styles.voiceErrorText,
            { paddingBottom: composerPadding, paddingTop: theme.spacing.xs },
          ]}
        >
          {voiceError}
        </Text>
      )}
    </KeyboardAvoidingView>
  );
}
