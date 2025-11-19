import { VOICE_PITCH_PRESETS, VOICE_RATE_PRESETS } from "@constants/voice";
import { useAuth } from "@context/AuthContext";
import { useVoiceSettings } from "@context/VoiceSettingsContext";
import { useNetworkStatus } from "@hooks/useNetworkStatus";
import { markStartupEvent } from "@hooks/useStartupProfiler";
import { useVoiceInput } from "@hooks/useVoiceInput";
import { useVoicePlayback } from "@hooks/useVoicePlayback";
import { sendMessage } from "@services/chat";
import { loadChatState, persistChatState } from "@services/chatCache";
import { normalizeTherapistRecommendations } from "@services/recommendations";
import { useTheme } from "@theme/ThemeProvider";
import { getAcademicSwitchColors } from "@theme/switchColors";
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
  zh: "请你自由地告诉我你现在经历的事情或出现的想法。不需要限定为情绪，也可以是任意一个浮现的念头。",
  en: "Please feel free to tell me whatever you are currently experiencing or thinking. It does not have to be a feeling—any spontaneous thought is welcome.",
  ru: "Свободно опишите, что именно вы переживаете или думаете сейчас. Это не обязательно про эмоции — любое возникшее наблюдение подойдёт.",
} as const;

const PSYCHODYNAMIC_QUOTES = [
  {
    id: "inner-world",
    zh: "每一个念头都承载着内在世界的一部分。",
    en: "Every thought, no matter how small, carries a piece of the inner world.",
    ru: "Каждая мысль, какой бы малой она ни была, несёт частицу внутреннего мира.",
  },
  {
    id: "beneath-surface",
    zh: "浮现于脑海的内容，往往映射着更深处的自我。",
    en: "What arises in your mind often reflects what lives beneath the surface.",
    ru: "То, что всплывает в сознании, часто отражает то, что живёт в глубине.",
  },
  {
    id: "connected",
    zh: "看似随机的念头可能比想象中更紧密相连。",
    en: "What feels random may be more connected than it seems.",
    ru: "То, что кажется случайным, может быть связаны гораздо теснее, чем видится.",
  },
  {
    id: "spontaneous",
    zh: "自发的表述蕴含洞见——此刻出现的一切都被欢迎。",
    en: "There is insight in the spontaneous — whatever comes up is welcome here.",
    ru: "В спонтанном отклике есть понимание — здесь приветствуется всё, что всплывает.",
  },
] as const;

const QUOTE_ATTRIBUTION = {
  zh: "—— 精神动力学提示",
  en: "— Psychodynamic reflection",
  ru: "— Психодинамическое наблюдение",
} as const;

const GLASS_INTENSITY = Platform.OS === "ios" ? 145 : 165;

type PromptLocale = keyof typeof PROMPT_COPY;

function resolvePromptLocale(locale: string | null | undefined): PromptLocale {
  const fallback: PromptLocale = "zh";
  if (!locale) {
    return fallback;
  }
  const normalized = locale.toLowerCase();
  if (normalized.startsWith("ru")) {
    return "ru";
  }
  if (normalized.startsWith("en")) {
    return "en";
  }
  if (normalized.startsWith("zh")) {
    return "zh";
  }
  return fallback;
}

type ChatScreenProps = {
  onNavigateBack?: () => void;
  onOpenSettings?: () => void;
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
  locale,
}: {
  recommendation: TherapistRecommendation;
  locale: string;
}) {
  const theme = useTheme();
  const normalized = locale.toLowerCase();
  const isZh = normalized.startsWith("zh");
  const isRu = normalized.startsWith("ru");
  const styles = useMemo(
    () =>
      StyleSheet.create({
        card: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.md,
          gap: theme.spacing.sm,
        },
        header: {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        },
        nameBlock: {
          flex: 1,
          marginRight: theme.spacing.sm,
          gap: 2,
        },
        name: {
          fontSize: 18,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        title: {
          fontSize: 13,
          color: theme.colors.textSecondary,
        },
        scoreBadge: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.9,
          alignItems: "center",
          minWidth: 68,
        },
        scoreValue: {
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        scoreLabel: {
          fontSize: 11,
          color: theme.colors.textSecondary,
        },
        reason: {
          fontSize: 14,
          lineHeight: 20,
          color: theme.colors.textPrimary,
        },
        keywordRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        },
        keywordBadge: {
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.8,
          fontSize: 11,
          color: theme.colors.textSecondary,
        },
        metaRow: {
          flexDirection: "row",
          justifyContent: "space-between",
          gap: theme.spacing.sm,
        },
        metaLabel: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          minWidth: 56,
        },
        metaValue: {
          flex: 1,
          fontSize: 13,
          color: theme.colors.textPrimary,
        },
      }),
    [theme],
  );

  const scorePercent = `${Math.round(recommendation.score * 100)}%`;
  const specialtiesLabel =
    recommendation.specialties.length > 0
      ? recommendation.specialties.join(" · ")
      : isZh
        ? "未提供擅长领域"
        : isRu
          ? "Нет данных"
          : "Not provided";
  const languagesLabel =
    recommendation.languages.length > 0
      ? recommendation.languages.join(" / ")
      : isZh
        ? "未提供语言"
        : isRu
          ? "Не указано"
          : "Not provided";
  const priceLabel = `${recommendation.price} ${recommendation.currency}`;
  const matchLabel = isZh
    ? "匹配度"
    : isRu
      ? "Совпадение"
      : "Match";

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.nameBlock}>
          <Text style={styles.name}>{recommendation.name}</Text>
          {recommendation.title ? (
            <Text style={styles.title}>{recommendation.title}</Text>
          ) : null}
        </View>
        <View style={styles.scoreBadge}>
          <Text style={styles.scoreValue}>{scorePercent}</Text>
          <Text style={styles.scoreLabel}>{matchLabel}</Text>
        </View>
      </View>
      {recommendation.reason && (
        <Text style={styles.reason}>{recommendation.reason}</Text>
      )}
      {recommendation.matchedKeywords.length > 0 && (
        <View style={styles.keywordRow}>
          {recommendation.matchedKeywords.map((keyword) => (
            <Text key={keyword} style={styles.keywordBadge}>
              {keyword}
            </Text>
          ))}
        </View>
      )}
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>
          {isZh ? "擅长" : isRu ? "Профиль" : "Focus"}
        </Text>
        <Text style={styles.metaValue}>{specialtiesLabel}</Text>
      </View>
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>
          {isZh ? "语言" : isRu ? "Язык" : "Languages"}
        </Text>
        <Text style={styles.metaValue}>{languagesLabel}</Text>
      </View>
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>
          {isZh ? "费用" : isRu ? "Стоимость" : "Fee"}
        </Text>
        <Text style={styles.metaValue}>{priceLabel}</Text>
      </View>
    </View>
  );
}

function resolveVoiceStatusLabel(
  isRecording: boolean,
  isTranscribing: boolean,
  isOffline: boolean,
  isZh: boolean,
): string {
  if (isOffline) {
    return isZh ? "离线模式暂不可用" : "Unavailable while offline";
  }
  if (isTranscribing) {
    return isZh ? "语音识别中…" : "Transcribing…";
  }
  if (isRecording) {
    return isZh ? "保持按住录音" : "Hold to record";
  }
  return isZh ? "长按说话" : "Press and hold to speak";
}

export function ChatScreen({
  onNavigateBack,
  onOpenSettings,
}: ChatScreenProps) {
  const theme = useTheme();
  const switchColors = useMemo(() => getAcademicSwitchColors(theme), [theme]);
  const { tokens, userId } = useAuth();
  const cacheMarkedRef = useRef(false);
  const screenVisibleRef = useRef(false);
  const firstResponseRef = useRef(false);
  const listRef = useRef<FlatList<MessageWithId>>(null);
  const insets = useSafeAreaInsets();
  const [activeLocale, setActiveLocale] = useState("zh-CN");
  const isZhLocale = activeLocale.toLowerCase().startsWith("zh");
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
  const [overflowVisible, setOverflowVisible] = useState(false);
  const [recommendations, setRecommendations] = useState<
    TherapistRecommendation[]
  >([]);
  const [memoryHighlights, setMemoryHighlights] = useState<
    { summary: string; keywords: string[] }[]
  >([]);
  const [isRestoring, setRestoring] = useState<boolean>(true);
  const networkStatus = useNetworkStatus(12000);
  const [voiceSettingsVisible, setVoiceSettingsVisible] = useState(false);
  const voicePlaybackStateLabel = voiceSettingsLoading
    ? isZhLocale
      ? "加载中"
      : "Loading"
    : isVoicePlaybackEnabled
      ? isZhLocale
        ? "已开启"
        : "Enabled"
      : isZhLocale
        ? "已关闭"
        : "Disabled";
  const isOffline =
    !networkStatus.isConnected || !networkStatus.isInternetReachable;
  const composerPadding = useMemo(
    () => Math.max(insets.bottom, theme.spacing.sm),
    [insets.bottom, theme.spacing.sm],
  );
  const keyboardVerticalOffset =
    Platform.OS === "ios" ? insets.top + theme.spacing.lg : 0;
  const androidRipple = useMemo(
    () =>
      Platform.OS === "android"
        ? { color: "rgba(255,255,255,0.2)", foreground: true }
        : undefined,
    [],
  );

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
        headerRight: {
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
        overflowButton: {
          width: 42,
          height: 42,
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "transparent",
        },
        overflowIcon: {
          fontSize: 18,
          color: theme.colors.textSecondary,
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
          width: 48,
          height: 56,
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
          borderColor: theme.colors.textPrimary,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.sm,
          width: "100%",
          alignItems: "center",
          backgroundColor: "transparent",
        },
        voiceButtonActive: {
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
        inputRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
        },
        input: {
          flex: 1,
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
          backgroundColor: "transparent",
        },
        chipActive: {
          borderColor: theme.colors.primary,
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
        overflowModal: {
          flex: 1,
          padding: theme.spacing.lg,
          justifyContent: "flex-start",
          alignItems: "flex-end",
          backgroundColor: "rgba(5,12,22,0.45)",
        },
        overflowBackdrop: {
          ...StyleSheet.absoluteFillObject,
        },
        overflowCard: {
          width: 260,
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.lg,
          gap: theme.spacing.md,
          marginTop: Platform.OS === "ios" ? insets.top : theme.spacing.lg,
        },
        overflowTitle: {
          fontSize: 16,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        overflowAction: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
          backgroundColor: "rgba(255,255,255,0.25)",
        },
        overflowActionLabel: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        overflowActionHint: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          lineHeight: 18,
        },
      }),
    [insets.top, theme],
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
        setRecommendations(
          normalizeTherapistRecommendations(cached.recommendations),
        );
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
      setRecommendations(
        normalizeTherapistRecommendations(response.recommendations),
      );
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
  const { promptText, quoteText, quoteAttribution } = useMemo(() => {
    const localeKey = resolvePromptLocale(activeLocale);
    const prompt = PROMPT_COPY[localeKey];
    const quoteOptions = PSYCHODYNAMIC_QUOTES.map(
      (entry) => entry[localeKey] ?? entry.en,
    );
    const quoteIndex =
      quoteOptions.length > 0
        ? Math.floor(Math.random() * quoteOptions.length)
        : 0;
    return {
      promptText: prompt,
      quoteText: quoteOptions[quoteIndex] ?? quoteOptions[0] ?? "",
      quoteAttribution:
        QUOTE_ATTRIBUTION[localeKey] ?? QUOTE_ATTRIBUTION.en,
    };
  }, [activeLocale]);
  const recommendationIntro = isZhLocale
    ? "根据你和 AI 的对话，我们推荐下列治疗师，并附上简短理由。"
    : "Based on your conversations with the AI, we recommend these therapists and short rationales.";
  const overflowTitle = isZhLocale ? "更多选项" : "More options";
  const overflowSettingsLabel = isZhLocale ? "打开设置" : "Open Settings";
  const overflowSettingsHint = isZhLocale
    ? "切换配色、语音播报与账户偏好。"
    : "Adjust palette, voice playback, and account preferences.";
  const composerPlaceholder = isZhLocale
    ? "请把此刻浮现的念头或观察输入在这里。"
    : "Share whatever thought or observation is present.";
  const modalTitle = isZhLocale ? "语音播报设置" : "Voice playback settings";
  const modalEnableLabel = isZhLocale
    ? "启用语音播报"
    : "Enable playback";
  const modalRateLabel = isZhLocale ? "语速" : "Rate";
  const modalPitchLabel = isZhLocale ? "音调" : "Pitch";
  const modalHintLabel = isZhLocale
    ? "每条 AI 回复都会以当前语速和音调播报。"
    : "Each reply will play using the selected rate and pitch.";
  const modalDoneLabel = isZhLocale ? "完成" : "Done";
  const renderListHeader = useCallback(() => {
    return (
      <View style={styles.listHeader}>
        <BlurView
          intensity={GLASS_INTENSITY + 5}
          tint="light"
          style={styles.promptCard}
        >
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
                  {String.fromCharCode(65 + index)}.{" "}
                  {recommendation.reason || (isZhLocale ? "匹配主题" : "Contextual match")}
                </Text>
                <RecommendationCard
                  recommendation={recommendation}
                  locale={activeLocale}
                />
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
      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.header}>
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
        <View style={styles.headerRight}>
          <Text style={styles.headerMeta}>
            {isZhLocale
              ? "心理动力 · 学术语气"
              : "Psychodynamic · Academic tone"}
          </Text>
          {onOpenSettings && (
            <Pressable
              android_ripple={androidRipple}
              accessibilityRole="button"
              accessibilityLabel={
                isZhLocale
                  ? "打开更多操作，包括设置入口"
                  : "Open overflow actions, including Settings"
              }
              style={styles.overflowButton}
              onPress={() => setOverflowVisible(true)}
            >
              <Text style={styles.overflowIcon}>⋯</Text>
            </Pressable>
          )}
        </View>
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
          intensity={GLASS_INTENSITY + 5}
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
              <View style={styles.inputRow}>
                {voiceSupported && (
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
                )}
                <TextInput
                  placeholder={composerPlaceholder}
                  placeholderTextColor={theme.colors.textSecondary}
                  value={inputValue}
                  onChangeText={handleInputChange}
                  style={styles.input}
                  editable={
                    !isSending && !isVoiceRecording && !isVoiceTranscribing
                  }
                  multiline
                />
              </View>
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
      {onOpenSettings && (
        <Modal
          visible={overflowVisible}
          transparent
          animationType="fade"
          onRequestClose={() => setOverflowVisible(false)}
        >
          <View style={styles.overflowModal}>
            <Pressable
              style={styles.overflowBackdrop}
              onPress={() => setOverflowVisible(false)}
            />
            <BlurView
              intensity={GLASS_INTENSITY}
              tint="light"
              style={styles.overflowCard}
            >
              <Text style={styles.overflowTitle}>{overflowTitle}</Text>
              <Pressable
                style={styles.overflowAction}
                android_ripple={androidRipple}
                onPress={() => {
                  setOverflowVisible(false);
                  Haptics.selectionAsync().catch(() => undefined);
                  onOpenSettings();
                }}
              >
                <Text style={styles.overflowActionLabel}>
                  {overflowSettingsLabel}
                </Text>
                <Text style={styles.overflowActionHint}>
                  {overflowSettingsHint}
                </Text>
              </Pressable>
            </BlurView>
          </View>
        </Modal>
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
                trackColor={{
                  true: switchColors.trackTrue,
                  false: switchColors.trackFalse,
                }}
                thumbColor={
                  isVoicePlaybackEnabled
                    ? switchColors.thumbTrue
                    : switchColors.thumbFalse
                }
                ios_backgroundColor={switchColors.iosFalse}
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
