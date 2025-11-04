import { useAuth } from "@context/AuthContext";
import { useVoiceSettings } from "@context/VoiceSettingsContext";
import { useNetworkStatus } from "@hooks/useNetworkStatus";
import { markStartupEvent } from "@hooks/useStartupProfiler";
import { useVoiceInput, type VoiceInputMode } from "@hooks/useVoiceInput";
import { useVoicePlayback } from "@hooks/useVoicePlayback";
import { sendMessage } from "@services/chat";
import { loadChatState, persistChatState } from "@services/chatCache";
import { useTheme } from "@theme/ThemeProvider";
import * as Haptics from "expo-haptics";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Switch,
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
  mode: VoiceInputMode,
  supported: boolean,
  isOffline: boolean,
  localSupported: boolean,
): string {
  if (!supported) {
    if (mode === "local") {
      return "设备暂不支持离线语音识别";
    }
    if (isOffline && !localSupported) {
      return "离线模式下语音识别不可用";
    }
    return "语音服务暂不可用";
  }
  if (isTranscribing) {
    return mode === "local" ? "本地识别中…" : "语音识别中…";
  }
  if (isRecording) {
    return mode === "local" ? "松开结束识别" : "保持按住录音";
  }
  if (mode === "local") {
    return isOffline ? "离线语音识别已启用" : "长按进行离线识别";
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
  const networkStatus = useNetworkStatus(12000);
  const isOffline =
    !networkStatus.isConnected || !networkStatus.isInternetReachable;
  const {
    supported: voiceSupported,
    isRecording: isVoiceRecording,
    isTranscribing: isVoiceTranscribing,
    error: voiceError,
    start: startVoiceInput,
    stop: stopVoiceInput,
    cancel: cancelVoiceInput,
    clearError: clearVoiceError,
    mode: voiceMode,
    localSupported: localVoiceSupported,
    remoteSupported: remoteVoiceSupported,
  } = useVoiceInput(activeLocale, tokens?.accessToken ?? null, {
    preferLocal: isOffline,
  });
  const {
    enabled: isVoicePlaybackEnabled,
    setEnabled: setVoicePlaybackEnabled,
    rate: voicePlaybackRate,
    pitch: voicePlaybackPitch,
    setRate: setVoicePlaybackRate,
    setPitch: setVoicePlaybackPitch,
    loading: voiceSettingsLoading,
  } = useVoiceSettings();
  const {
    speak: speakVoiceResponse,
    stop: stopVoicePlayback,
    speaking: isVoicePlaybackActive,
  } = useVoicePlayback();
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
  const [knowledgeSnippets, setKnowledgeSnippets] = useState<
    {
      entryId: string;
      title: string;
      summary: string;
      guidance: string[];
      source?: string;
    }[]
  >([]);
  const [isRestoring, setRestoring] = useState<boolean>(true);
  const [voiceSettingsVisible, setVoiceSettingsVisible] = useState(false);
  const ratePresets = useMemo(
    () => [
      { label: "慢速", value: 0.85 },
      { label: "标准", value: 1 },
      { label: "快速", value: 1.2 },
    ],
    [],
  );
  const pitchPresets = useMemo(
    () => [
      { label: "柔和", value: 0.9 },
      { label: "标准", value: 1 },
      { label: "明亮", value: 1.1 },
    ],
    [],
  );
  const voicePlaybackStateLabel = voiceSettingsLoading
    ? "加载中"
    : isVoicePlaybackEnabled
      ? "开启"
      : "关闭";
  const composerPadding = useMemo(
    () => Math.max(insets.bottom, theme.spacing.sm),
    [insets.bottom, theme.spacing.sm],
  );
  const keyboardVerticalOffset =
    Platform.OS === "ios" ? insets.top + theme.spacing.lg : 0;
  const androidRipple = useMemo(
    () =>
      Platform.OS === "android"
        ? { color: "rgba(37,99,235,0.12)", foreground: true }
        : undefined,
    [],
  );
  const canRenderVoiceButton = localVoiceSupported || remoteVoiceSupported;
  const remoteOfflineBlocked = voiceMode === "remote" && isOffline;
  const effectiveVoiceSupported = voiceSupported && !remoteOfflineBlocked;

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
        snippetCard: {
          borderRadius: theme.radius.md,
          backgroundColor: "rgba(14, 165, 233, 0.06)",
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
        },
        snippetTitle: {
          fontWeight: "600",
          color: theme.colors.textPrimary,
          fontSize: 16,
        },
        snippetSummary: {
          color: theme.colors.textSecondary,
          fontSize: 14,
        },
        snippetGuidance: {
          color: theme.colors.textPrimary,
          fontSize: 14,
          lineHeight: 20,
        },
        snippetSource: {
          marginTop: theme.spacing.xs,
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
        headerActions: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
        },
        headerTitle: {
          fontSize: 20,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        voiceSettingsButton: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          backgroundColor: theme.colors.surfaceMuted,
        },
        voiceSettingsLabel: {
          fontSize: 12,
          fontWeight: "600",
          color: theme.colors.textSecondary,
        },
        voiceSettingsValue: {
          fontSize: 14,
          color: theme.colors.primary,
        },
        voiceSettingsValueDisabled: {
          color: theme.colors.textSecondary,
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
        offlineNotice: {
          color: theme.colors.warning,
          textAlign: "center",
          fontSize: 13,
          paddingHorizontal: theme.spacing.md,
          marginTop: theme.spacing.sm,
        },
        modalOverlay: {
          flex: 1,
          backgroundColor: "rgba(15,23,42,0.6)",
          justifyContent: "center",
          alignItems: "center",
          padding: theme.spacing.lg,
        },
        modalBackdrop: {
          ...StyleSheet.absoluteFillObject,
        },
        modalCard: {
          width: "100%",
          maxWidth: 360,
          borderRadius: theme.radius.lg,
          backgroundColor: theme.colors.surfaceCard,
          padding: theme.spacing.lg,
          gap: theme.spacing.md,
        },
        modalTitle: {
          fontSize: 18,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        switchRow: {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        },
        switchLabel: {
          fontSize: 16,
          color: theme.colors.textPrimary,
        },
        modalSection: {
          gap: theme.spacing.sm,
        },
        modalSectionTitle: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textSecondary,
        },
        chipRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.sm,
        },
        chip: {
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs,
          backgroundColor: theme.colors.surfaceMuted,
        },
        chipActive: {
          borderColor: theme.colors.primary,
          backgroundColor: "rgba(37,99,235,0.12)",
        },
        chipLabel: {
          fontSize: 13,
          color: theme.colors.textSecondary,
        },
        chipLabelActive: {
          color: theme.colors.primary,
          fontWeight: "600",
        },
        modalHint: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        modalClose: {
          alignSelf: "flex-end",
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs,
          borderRadius: theme.radius.md,
          backgroundColor: theme.colors.primary,
        },
        modalCloseLabel: {
          color: "#fff",
          fontWeight: "600",
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

  useEffect(
    () => () => {
      stopVoicePlayback();
    },
    [stopVoicePlayback],
  );

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
        setKnowledgeSnippets(cached.knowledgeSnippets ?? []);
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
      knowledgeSnippets,
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
    knowledgeSnippets,
    isRestoring,
    activeLocale,
  ]);

  useEffect(() => {
    if (!isOffline && error && error.includes("离线状态")) {
      setError(null);
    }
  }, [isOffline, error]);

  useEffect(() => {
    if (!isRestoring && !screenVisibleRef.current) {
      markStartupEvent("chat-screen-visible");
      screenVisibleRef.current = true;
    }
  }, [isRestoring]);

  const handleInputChange = useCallback(
    (value: string) => {
      clearVoiceError();
      if (isVoicePlaybackActive) {
        stopVoicePlayback();
      }
      setInputValue(value);
    },
    [clearVoiceError, isVoicePlaybackActive, stopVoicePlayback],
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
    if (!effectiveVoiceSupported) {
      return;
    }
    clearVoiceError();
    if (isVoicePlaybackActive) {
      stopVoicePlayback();
    }
    if (Platform.OS === "ios" || Platform.OS === "android") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {
        // Haptic feedback may not be available on all devices.
      });
    }
    startVoiceInput(handleVoiceTranscript).catch((error) => {
      console.warn("Failed to start voice input", error);
    });
  }, [
    clearVoiceError,
    isVoicePlaybackActive,
    startVoiceInput,
    handleVoiceTranscript,
    effectiveVoiceSupported,
    stopVoicePlayback,
  ]);

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

  const handleVoicePlaybackToggle = useCallback(
    (value: boolean) => {
      setVoicePlaybackEnabled(value);
      if (!value) {
        stopVoicePlayback();
      }
    },
    [setVoicePlaybackEnabled, stopVoicePlayback],
  );

  const handleSelectVoiceRate = useCallback(
    (value: number) => {
      setVoicePlaybackRate(value);
    },
    [setVoicePlaybackRate],
  );

  const handleSelectVoicePitch = useCallback(
    (value: number) => {
      setVoicePlaybackPitch(value);
    },
    [setVoicePlaybackPitch],
  );

  const closeVoiceSettings = useCallback(() => {
    setVoiceSettingsVisible(false);
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!tokens || !userId || trimmed.length === 0) {
      return;
    }
    if (isVoicePlaybackActive) {
      stopVoicePlayback();
    }
    if (isOffline) {
      setError("当前处于离线状态，请联网后再发送消息。");
      if (Platform.OS === "ios" || Platform.OS === "android") {
        Haptics.notificationAsync(
          Haptics.NotificationFeedbackType.Warning,
        ).catch(() => {
          // Haptic feedback is best-effort.
        });
      }
      return;
    }
    const userMessage: MessageWithId = {
      id: `${Date.now()}-user`,
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    appendMessage(userMessage);
    setInputValue("");
    if (Platform.OS === "ios" || Platform.OS === "android") {
      Haptics.selectionAsync().catch(() => {
        // Selection feedback missing support on some devices; ignore failures.
      });
    }
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
      const playbackLocale = response.resolvedLocale ?? activeLocale;
      speakVoiceResponse({
        text: assistantMessage.content,
        locale: playbackLocale,
      });
      setRecommendations(response.recommendations);
      setMemoryHighlights(response.memoryHighlights);
      setKnowledgeSnippets(response.knowledgeSnippets);
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
  }, [
    tokens,
    userId,
    inputValue,
    sessionId,
    activeLocale,
    isOffline,
    appendMessage,
    speakVoiceResponse,
    isVoicePlaybackActive,
    stopVoicePlayback,
  ]);

  const sendDisabled = isSending || isOffline || inputValue.trim().length === 0;
  const voiceDisabled =
    isSending || isVoiceTranscribing || !effectiveVoiceSupported;
  const voiceStatusText = resolveVoiceStatusLabel(
    isVoiceRecording,
    isVoiceTranscribing,
    voiceMode,
    effectiveVoiceSupported,
    isOffline,
    localVoiceSupported,
  );
  const voiceButtonLabel = (() => {
    if (!effectiveVoiceSupported) {
      if (voiceMode === "local" && !localVoiceSupported) {
        return "不支持离线";
      }
      if (voiceMode === "remote" && isOffline) {
        return "离线不可用";
      }
      return "暂不可用";
    }
    if (isVoiceRecording) {
      return "松开结束";
    }
    if (voiceMode === "local") {
      return "按住离线识别";
    }
    return "按住语音";
  })();

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={keyboardVerticalOffset}
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MindWell 对话</Text>
        <View style={styles.headerActions}>
          <Pressable
            android_ripple={androidRipple}
            accessibilityRole="button"
            accessibilityLabel="打开语音播报设置"
            onPress={() => setVoiceSettingsVisible(true)}
            disabled={voiceSettingsLoading}
            style={[
              styles.voiceSettingsButton,
              voiceSettingsLoading && { opacity: 0.6 },
            ]}
          >
            <Text style={styles.voiceSettingsLabel}>语音播报</Text>
            <Text
              style={[
                styles.voiceSettingsValue,
                (!isVoicePlaybackEnabled || voiceSettingsLoading) &&
                  styles.voiceSettingsValueDisabled,
              ]}
            >
              {voicePlaybackStateLabel}
            </Text>
          </Pressable>
          <Pressable
            android_ripple={androidRipple}
            onPress={logout}
            style={styles.logoutButton}
          >
            <Text style={styles.logoutLabel}>退出</Text>
          </Pressable>
        </View>
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
          keyboardDismissMode={
            Platform.OS === "ios" ? "interactive" : "on-drag"
          }
          contentInset={{ bottom: composerPadding }}
          contentInsetAdjustmentBehavior={
            Platform.OS === "ios" ? "always" : "automatic"
          }
          scrollIndicatorInsets={{ bottom: composerPadding }}
          initialNumToRender={12}
          removeClippedSubviews={Platform.OS === "android"}
          maintainVisibleContentPosition={
            Platform.OS === "ios"
              ? { minIndexForVisible: 0, autoscrollToTopThreshold: 20 }
              : undefined
          }
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

        {knowledgeSnippets.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>心理教育提示</Text>
            {knowledgeSnippets.map((snippet) => (
              <View key={snippet.entryId} style={styles.snippetCard}>
                <Text style={styles.snippetTitle}>{snippet.title}</Text>
                <Text style={styles.snippetSummary}>{snippet.summary}</Text>
                {snippet.guidance.slice(0, 2).map((line, index) => (
                  <Text key={`${snippet.entryId}-${index}`} style={styles.snippetGuidance}>
                    {"• " + line}
                  </Text>
                ))}
                {snippet.source ? (
                  <Text style={styles.snippetSource}>{snippet.source}</Text>
                ) : null}
              </View>
            ))}
          </View>
        )}
      </View>

      {isOffline && (
        <Text style={styles.offlineNotice}>
          当前离线，已切换到本地缓存模式。
        </Text>
      )}

      <View
        style={[
          styles.composer,
          { paddingBottom: composerPadding, paddingTop: theme.spacing.sm },
        ]}
      >
        {canRenderVoiceButton && (
          <View style={styles.voiceContainer}>
            <Pressable
              android_ripple={androidRipple}
              accessibilityRole="button"
              accessibilityLabel="按住进行语音输入"
              onPressIn={handleVoiceStart}
              onPressOut={handleVoiceStop}
              onTouchCancel={handleVoiceCancel}
              disabled={voiceDisabled}
              style={[
                styles.voiceButton,
                isVoiceRecording && styles.voiceButtonActive,
                voiceDisabled && styles.voiceButtonDisabled,
              ]}
            >
              <Text
                style={[
                  styles.voiceButtonLabel,
                  isVoiceRecording && styles.voiceButtonLabelActive,
                  !effectiveVoiceSupported && { opacity: 0.7 },
                ]}
              >
                {voiceButtonLabel}
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
                {voiceStatusText}
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
          android_ripple={androidRipple}
          onPress={handleSend}
          style={[styles.sendButton, { opacity: sendDisabled ? 0.5 : 1 }]}
          disabled={sendDisabled}
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
      <Modal
        visible={voiceSettingsVisible}
        transparent
        animationType="fade"
        onRequestClose={closeVoiceSettings}
      >
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={closeVoiceSettings}
            android_ripple={{ color: "transparent" }}
          />
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>语音播报设置</Text>
            <View style={styles.switchRow}>
              <Text style={styles.switchLabel}>启用语音播报</Text>
              <Switch
                value={isVoicePlaybackEnabled}
                onValueChange={handleVoicePlaybackToggle}
              />
            </View>
            <View style={styles.modalSection}>
              <Text style={styles.modalSectionTitle}>语速</Text>
              <View style={styles.chipRow}>
                {ratePresets.map((preset) => {
                  const isActive =
                    Math.abs(voicePlaybackRate - preset.value) < 0.01;
                  return (
                    <Pressable
                      key={preset.value}
                      android_ripple={androidRipple}
                      onPress={() => handleSelectVoiceRate(preset.value)}
                      style={[styles.chip, isActive && styles.chipActive]}
                    >
                      <Text
                        style={[
                          styles.chipLabel,
                          isActive && styles.chipLabelActive,
                        ]}
                      >
                        {preset.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            <View style={styles.modalSection}>
              <Text style={styles.modalSectionTitle}>音色</Text>
              <View style={styles.chipRow}>
                {pitchPresets.map((preset) => {
                  const isActive =
                    Math.abs(voicePlaybackPitch - preset.value) < 0.01;
                  return (
                    <Pressable
                      key={preset.value}
                      android_ripple={androidRipple}
                      onPress={() => handleSelectVoicePitch(preset.value)}
                      style={[styles.chip, isActive && styles.chipActive]}
                    >
                      <Text
                        style={[
                          styles.chipLabel,
                          isActive && styles.chipLabelActive,
                        ]}
                      >
                        {preset.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            {isVoicePlaybackActive && (
              <Text style={styles.modalHint}>播报中…</Text>
            )}
            <Pressable
              android_ripple={androidRipple}
              style={styles.modalClose}
              onPress={closeVoiceSettings}
            >
              <Text style={styles.modalCloseLabel}>完成</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}
