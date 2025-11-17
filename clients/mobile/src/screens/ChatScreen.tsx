import { VOICE_PITCH_PRESETS, VOICE_RATE_PRESETS } from "@constants/voice";
import { useAuth } from "@context/AuthContext";
import { useVoiceSettings } from "@context/VoiceSettingsContext";
import { useNetworkStatus } from "@hooks/useNetworkStatus";
import { markStartupEvent } from "@hooks/useStartupProfiler";
import { useVoiceInput } from "@hooks/useVoiceInput";
import { useVoicePlayback } from "@hooks/useVoicePlayback";
import { sendMessage } from "@services/chat";
import { loadChatState, persistChatState } from "@services/chatCache";
import { useTheme } from "@theme/ThemeProvider";
import { BlurView } from "expo-blur";
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

const PROMPT_COPY = {
  zh: "请自由地描述此刻正在经历的事情、感受到的刺激，或任何刚刚浮现的念头。",
  en: "Please feel free to describe what you are experiencing right now—any observation or thought is welcome.",
};

const PSYCHODYNAMIC_QUOTES = [
  {
    id: "inner-world",
    zh: "每一个念头都承载着内在世界的一部分。",
    en: "Every thought, no matter how small, carries a piece of the inner world.",
  },
  {
    id: "beneath-surface",
    zh: "浮现于脑海的内容，往往映射着更深处的自我。",
    en: "What arises in your mind often reflects what lives beneath the surface.",
  },
  {
    id: "connected",
    zh: "看似随机的念头可能比想象中更紧密相连。",
    en: "What feels random may be more connected than it seems.",
  },
  {
    id: "spontaneous",
    zh: "自发的表述蕴含洞见——此刻出现的一切都被欢迎。",
    en: "There is insight in the spontaneous — whatever comes up is welcome here.",
  },
] as const;

type ChatScreenProps = {
  onNavigateBack?: () => void;
};

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
          flex: 1,
          backgroundColor: "transparent",
        },
        content: {
          flexGrow: 1,
          paddingHorizontal: theme.spacing.md,
        },
        header: {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          marginHorizontal: theme.spacing.md,
          marginTop: theme.spacing.md,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
        },
        headerLeft: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
        },
        backButton: {
          width: 42,
          height: 42,
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          alignItems: "center",
          justifyContent: "center",
        },
        backIcon: {
          fontSize: 18,
          color: theme.colors.textPrimary,
        },
        headerTitle: {
          fontSize: 20,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        headerMeta: {
          fontSize: 12,
          letterSpacing: 0.6,
          color: theme.colors.textSecondary,
        },
        listHeader: {
          paddingHorizontal: theme.spacing.md,
          paddingTop: theme.spacing.md,
          gap: theme.spacing.md,
        },
        promptCard: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.lg,
          gap: theme.spacing.sm,
        },
        promptLabel: {
          fontSize: 12,
          letterSpacing: 0.6,
          color: theme.colors.textSecondary,
        },
        promptText: {
          fontSize: 16,
          lineHeight: 24,
          color: theme.colors.textPrimary,
        },
        quoteText: {
          fontStyle: "italic",
          color: theme.colors.textSecondary,
        },
        quoteAttribution: {
          textAlign: "right",
          color: theme.colors.textSecondary,
          fontSize: 13,
        },
        section: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.md,
          gap: theme.spacing.sm,
        },
        sectionTitle: {
          fontSize: 16,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        sectionSubtitle: {
          fontSize: 13,
          lineHeight: 20,
          color: theme.colors.textSecondary,
        },
        recommendationWrapper: {
          gap: theme.spacing.xs,
        },
        recommendationLead: {
          fontSize: 13,
          color: theme.colors.textSecondary,
        },
        highlight: {
          borderRadius: theme.radius.md,
          backgroundColor: "rgba(74,144,121,0.08)",
          padding: theme.spacing.md,
          borderWidth: 1,
          borderColor: "rgba(255,255,255,0.4)",
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
        offlineNotice: {
          color: theme.colors.warning,
          textAlign: "center",
          fontSize: 13,
          paddingHorizontal: theme.spacing.md,
          marginTop: theme.spacing.sm,
        },
        composerShell: {
          paddingHorizontal: theme.spacing.md,
          marginTop: theme.spacing.md,
        },
        composer: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.md,
        },
        composerRow: {
          flexDirection: "row",
          gap: theme.spacing.md,
        },
        voiceColumn: {
          width: 96,
          alignItems: "center",
          gap: theme.spacing.sm,
        },
        voiceArrowButton: {
          width: 52,
          height: 52,
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "transparent",
        },
        voiceArrowIcon: {
          fontSize: 22,
          color: theme.colors.textPrimary,
        },
        voiceButton: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.sm,
          width: "100%",
          alignItems: "center",
          backgroundColor: "rgba(255,255,255,0.2)",
        },
        voiceButtonActive: {
          borderColor: theme.colors.primary,
          backgroundColor: "rgba(74,144,121,0.15)",
        },
        voiceButtonDisabled: {
          opacity: 0.4,
        },
        voiceButtonLabel: {
          color: theme.colors.textPrimary,
          fontWeight: "600",
        },
        voiceButtonLabelActive: {
          color: theme.colors.primary,
        },
        voiceStatusRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.xs * 0.75,
        },
        voiceStatusText: {
          color: theme.colors.textSecondary,
          fontSize: 12,
        },
        voiceModeStatus: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          textAlign: "center",
        },
        inputColumn: {
          flex: 1,
          gap: theme.spacing.sm,
        },
        input: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.lg,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          fontSize: 16,
          minHeight: 56,
          backgroundColor: "rgba(255,255,255,0.5)",
          color: theme.colors.textPrimary,
        },
        sendButton: {
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          borderRadius: theme.radius.pill,
          paddingVertical: theme.spacing.sm,
          alignItems: "center",
          backgroundColor: "transparent",
        },
        sendLabel: {
          fontWeight: "700",
          letterSpacing: 0.8,
          color: theme.colors.textPrimary,
        },
        voiceErrorText: {
          color: theme.colors.danger,
          fontSize: 12,
          paddingHorizontal: theme.spacing.md,
          paddingBottom: theme.spacing.xs,
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
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
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
          backgroundColor: "rgba(255,255,255,0.15)",
        },
        chipActive: {
          borderColor: theme.colors.primary,
          backgroundColor: "rgba(74,144,121,0.15)",
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
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
        },
        modalCloseLabel: {
          color: theme.colors.textPrimary,
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
    if (isOffline) {
      return;
    }
    clearVoiceError();
    if (Platform.OS === "ios" || Platform.OS === "android") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {
        // Haptic feedback may not be available on all devices.
      });
    }
    startVoiceInput(handleVoiceTranscript).catch((error) => {
      console.warn("Failed to start voice input", error);
    });
  }, [clearVoiceError, startVoiceInput, handleVoiceTranscript, isOffline]);

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
    if (isOffline) {
      setError(
        isZhLocale
          ? "当前处于离线状态，请联网后再发送消息。"
          : "You appear to be offline. Please reconnect before sending a message.",
      );
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
  ]);

  const sendDisabled = isSending || isOffline || inputValue.trim().length === 0;
  const recommendationIntro = isZhLocale
    ? "根据你和 AI 的对话，我们推荐下列治疗师，并附上简短理由。"
    : "Based on your conversations with the AI, we recommend these therapists and short rationales.";
  const renderListHeader = useCallback(() => {
    return (
      <View style={styles.listHeader}>
        <BlurView intensity={80} tint="light" style={styles.promptCard}>
          <Text style={styles.promptLabel}>
            {isZhLocale ? "开放式引导" : "Open prompt"}
          </Text>
          <Text style={styles.promptText}>{promptText}</Text>
          <Text style={styles.quoteText}>{`“${quoteText}”`}</Text>
          <Text style={styles.quoteAttribution}>{quoteAttribution}</Text>
        </BlurView>
        {recommendations.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {isZhLocale ? "AI 推荐治疗师" : "AI therapist suggestions"}
            </Text>
            <Text style={styles.sectionSubtitle}>{recommendationIntro}</Text>
            {recommendations.map((recommendation, index) => (
              <View
                key={recommendation.id}
                style={styles.recommendationWrapper}
              >
                <Text style={styles.recommendationLead}>
                  {String.fromCharCode(65 + index)}. {recommendation.summary}
                </Text>
                <RecommendationCard recommendation={recommendation} />
              </View>
            ))}
          </View>
        )}
        {memoryHighlights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {isZhLocale ? "疗程亮点" : "Therapy highlights"}
            </Text>
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
    );
  }, [
    isZhLocale,
    styles,
    promptText,
    quoteText,
    quoteAttribution,
    recommendations,
    memoryHighlights,
    recommendationIntro,
  ]);
  const voiceDisabled = isSending || isVoiceTranscribing || isOffline;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={keyboardVerticalOffset}
    >
      <BlurView intensity={85} tint="light" style={styles.header}>
        <View style={styles.headerLeft}>
          {onNavigateBack && (
            <Pressable
              android_ripple={androidRipple}
              accessibilityRole="button"
              accessibilityLabel={
                isZhLocale ? "返回上一屏" : "Return to previous tab"
              }
              style={styles.backButton}
              onPress={() => {
                Haptics.selectionAsync().catch(() => undefined);
                onNavigateBack();
              }}
            >
              <Text style={styles.backIcon}>←</Text>
            </Pressable>
          )}
          <Text style={styles.headerTitle}>
            {isZhLocale ? "MindWell 对话" : "MindWell Dialogue"}
          </Text>
        </View>
        <Text style={styles.headerMeta}>
          {isZhLocale
            ? "心理动力 · 学术语气"
            : "Psychodynamic · Academic tone"}
        </Text>
      </BlurView>

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
            {isZhLocale ? "正在恢复会话…" : "Restoring your session…"}
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
          ListHeaderComponent={renderListHeader}
        />
      )}

      {isOffline && (
        <Text style={styles.offlineNotice}>
          {isZhLocale
            ? "当前离线，已切换到本地缓存模式。"
            : "Offline mode active — showing cached conversation."}
        </Text>
      )}

      <View style={styles.composerShell}>
        <BlurView
          intensity={90}
          tint="light"
          style={[styles.composer, { paddingBottom: composerPadding }]}
        >
          <View style={styles.composerRow}>
            {voiceSupported && (
              <View style={styles.voiceColumn}>
                <Pressable
                  android_ripple={androidRipple}
                  accessibilityRole="button"
                  accessibilityLabel={
                    isZhLocale
                      ? "打开语音播报设置"
                      : "Open voice playback preferences"
                  }
                  onPress={() => setVoiceSettingsVisible(true)}
                  style={styles.voiceArrowButton}
                >
                  <Text style={styles.voiceArrowIcon}>↢</Text>
                </Pressable>
                <Pressable
                  android_ripple={androidRipple}
                  accessibilityRole="button"
                  accessibilityLabel={
                    isZhLocale ? "按住进行语音输入" : "Hold to record voice input"
                  }
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
                      isOffline && { opacity: 0.7 },
                    ]}
                  >
                    {isOffline
                      ? isZhLocale
                        ? "离线不可用"
                        : "Offline only"
                      : isVoiceRecording
                        ? isZhLocale
                          ? "松开结束"
                          : "Release to stop"
                        : isZhLocale
                          ? "按住语音"
                          : "Hold to speak"}
                  </Text>
                </Pressable>
                <View style={styles.voiceStatusRow}>
                  {isVoiceTranscribing && (
                    <ActivityIndicator
                      size="small"
                      color={theme.colors.primary}
                    />
                  )}
                  <Text style={styles.voiceStatusText}>
                    {resolveVoiceStatusLabel(
                      isVoiceRecording,
                      isVoiceTranscribing,
                      isOffline,
                      isZhLocale,
                    )}
                  </Text>
                </View>
                <Text style={styles.voiceModeStatus}>
                  {isZhLocale
                    ? `播报：${voicePlaybackStateLabel}`
                    : `Playback: ${voicePlaybackStateLabel}`}
                </Text>
              </View>
            )}
            <View style={styles.inputColumn}>
              <TextInput
                placeholder={composerPlaceholder}
                placeholderTextColor={theme.colors.textSecondary}
                value={inputValue}
                onChangeText={handleInputChange}
                style={styles.input}
                editable={!isSending && !isVoiceRecording && !isVoiceTranscribing}
                multiline
              />
              <Pressable
                android_ripple={androidRipple}
                onPress={handleSend}
                style={[styles.sendButton, { opacity: sendDisabled ? 0.5 : 1 }]}
                disabled={sendDisabled}
              >
                <Text style={styles.sendLabel}>
                  {isSending
                    ? isZhLocale
                      ? "发送中…"
                      : "Sending…"
                    : isZhLocale
                      ? "发送"
                      : "Send"}
                </Text>
              </Pressable>
            </View>
          </View>
        </BlurView>
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
            <Text style={styles.modalTitle}>{modalTitle}</Text>
            <View style={styles.switchRow}>
              <Text style={styles.switchLabel}>{modalEnableLabel}</Text>
              <Switch
                value={isVoicePlaybackEnabled}
                onValueChange={handleVoicePlaybackToggle}
              />
            </View>
            <View style={styles.modalSection}>
              <Text style={styles.modalSectionTitle}>{modalRateLabel}</Text>
              <View style={styles.chipRow}>
                {VOICE_RATE_PRESETS.map((preset) => {
                  const isActive =
                    Math.abs(voicePlaybackRate - preset.value) < 0.01;
                  return (
                    <Pressable
                      key={preset.id}
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
                        {isZhLocale ? preset.labelZh : preset.labelEn}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            <View style={styles.modalSection}>
              <Text style={styles.modalSectionTitle}>{modalPitchLabel}</Text>
              <View style={styles.chipRow}>
                {VOICE_PITCH_PRESETS.map((preset) => {
                  const isActive =
                    Math.abs(voicePlaybackPitch - preset.value) < 0.01;
                  return (
                    <Pressable
                      key={preset.id}
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
                        {isZhLocale ? preset.labelZh : preset.labelEn}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            {isVoicePlaybackActive && (
              <Text style={styles.modalHint}>{modalHintLabel}</Text>
            )}
            <Pressable
              android_ripple={androidRipple}
              style={styles.modalClose}
              onPress={closeVoiceSettings}
            >
              <Text style={styles.modalCloseLabel}>{modalDoneLabel}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}
