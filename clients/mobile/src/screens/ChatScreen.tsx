import { VOICE_PITCH_PRESETS, VOICE_RATE_PRESETS } from "@constants/voice";
import { useAuth } from "@context/AuthContext";
import { useLocale } from "@context/LocaleContext";
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
import { toCopyLocale, type CopyLocale } from "@utils/locale";
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

const CHAT_COPY = {
  zh: {
    noSpecialties: "未提供擅长领域",
    noLanguages: "未提供语言",
    matchLabel: "匹配度",
    focusLabel: "擅长",
    languageLabel: "语言",
    feeLabel: "费用",
    voiceUnavailable: "离线模式暂不可用",
    voiceTranscribing: "语音识别中…",
    voiceRecording: "保持按住录音",
    voiceIdle: "长按说话",
    voicePlaybackLoading: "加载中",
    voicePlaybackEnabled: "已开启",
    voicePlaybackDisabled: "已关闭",
    offlineSendError: "当前处于离线状态，请联网后再发送消息。",
    sendErrorFallback: "发送消息失败，请稍后重试。",
    recommendationIntro: "根据你和 AI 的对话，我们推荐下列治疗师，并附上简短理由。",
    overflowTitle: "更多选项",
    overflowSettingsLabel: "打开设置",
    overflowSettingsHint: "切换配色、语音播报与账户偏好。",
    composerPlaceholder: "请把此刻浮现的念头或观察输入在这里。",
    modalTitle: "语音播报设置",
    modalEnableLabel: "启用语音播报",
    modalRateLabel: "语速",
    modalPitchLabel: "音调",
    modalHintLabel: "每条 AI 回复都会以当前语速和音调播报。",
    modalDoneLabel: "完成",
    promptLabel: "开放式引导",
    recommendationsTitle: "AI 推荐治疗师",
    recommendationFallback: "匹配主题",
    highlightsTitle: "疗程亮点",
    backLabel: "返回上一屏",
    headerTitle: "MindWell 对话",
    headerMeta: "心理动力 · 学术语气",
    overflowAria: "打开更多操作，包括设置入口",
    restoringLabel: "正在恢复会话…",
    offlineBanner: "当前离线，已切换到本地缓存模式。",
    voiceButtonTooltip: "按住进行语音输入",
    voiceButtonOffline: "离线不可用",
    voiceButtonRecording: "松开结束",
    voiceButtonIdle: "按住语音",
    playbackPrefix: "播报：",
    playbackSettingsLabel: "打开语音播报设置",
    sendingLabel: "发送中…",
    sendLabel: "发送",
  },
  en: {
    noSpecialties: "Not provided",
    noLanguages: "Not provided",
    matchLabel: "Match",
    focusLabel: "Focus",
    languageLabel: "Languages",
    feeLabel: "Fee",
    voiceUnavailable: "Unavailable while offline",
    voiceTranscribing: "Transcribing…",
    voiceRecording: "Hold to record",
    voiceIdle: "Press and hold to speak",
    voicePlaybackLoading: "Loading",
    voicePlaybackEnabled: "Enabled",
    voicePlaybackDisabled: "Disabled",
    offlineSendError: "You appear to be offline. Please reconnect before sending a message.",
    sendErrorFallback: "Failed to send message. Please try again.",
    recommendationIntro: "Based on your conversations with the AI, we recommend these therapists and short rationales.",
    overflowTitle: "More options",
    overflowSettingsLabel: "Open Settings",
    overflowSettingsHint: "Adjust palette, voice playback, and account preferences.",
    composerPlaceholder: "Share whatever thought or observation is present.",
    modalTitle: "Voice playback settings",
    modalEnableLabel: "Enable playback",
    modalRateLabel: "Rate",
    modalPitchLabel: "Pitch",
    modalHintLabel: "Each reply will play using the selected rate and pitch.",
    modalDoneLabel: "Done",
    promptLabel: "Open prompt",
    recommendationsTitle: "AI therapist suggestions",
    recommendationFallback: "Contextual match",
    highlightsTitle: "Therapy highlights",
    backLabel: "Return to previous tab",
    headerTitle: "MindWell Dialogue",
    headerMeta: "Psychodynamic · Academic tone",
    overflowAria: "Open overflow actions, including Settings",
    restoringLabel: "Restoring your session…",
    offlineBanner: "Offline mode active — showing cached conversation.",
    voiceButtonTooltip: "Hold to record voice input",
    voiceButtonOffline: "Offline only",
    voiceButtonRecording: "Release to stop",
    voiceButtonIdle: "Hold to speak",
    playbackPrefix: "Playback: ",
    playbackSettingsLabel: "Open voice playback preferences",
    sendingLabel: "Sending…",
    sendLabel: "Send",
  },
  ru: {
    noSpecialties: "Нет данных",
    noLanguages: "Не указано",
    matchLabel: "Совпадение",
    focusLabel: "Профиль",
    languageLabel: "Язык",
    feeLabel: "Стоимость",
    voiceUnavailable: "Недоступно офлайн",
    voiceTranscribing: "Расшифровка…",
    voiceRecording: "Удерживайте для записи",
    voiceIdle: "Нажмите и удерживайте, чтобы говорить",
    voicePlaybackLoading: "Загрузка",
    voicePlaybackEnabled: "Включено",
    voicePlaybackDisabled: "Выключено",
    offlineSendError: "Вы офлайн. Подключитесь к сети и отправьте снова.",
    sendErrorFallback: "Не удалось отправить сообщение. Попробуйте позже.",
    recommendationIntro: "По вашим разговорам с ИИ предлагаем терапевтов и краткие причины.",
    overflowTitle: "Больше опций",
    overflowSettingsLabel: "Открыть настройки",
    overflowSettingsHint: "Палитра, озвучка и параметры аккаунта.",
    composerPlaceholder: "Поделитесь любой мыслью или наблюдением сейчас.",
    modalTitle: "Настройки озвучки",
    modalEnableLabel: "Включить озвучку",
    modalRateLabel: "Скорость",
    modalPitchLabel: "Тон",
    modalHintLabel: "Каждый ответ будет озвучен с выбранной скоростью и тоном.",
    modalDoneLabel: "Готово",
    promptLabel: "Открытый запрос",
    recommendationsTitle: "Рекомендации терапевтов ИИ",
    recommendationFallback: "Контекстное совпадение",
    highlightsTitle: "Ключевые моменты",
    backLabel: "Вернуться на предыдущую вкладку",
    headerTitle: "MindWell Диалог",
    headerMeta: "Психодинамика · Академический тон",
    overflowAria: "Дополнительные действия, включая Настройки",
    restoringLabel: "Восстанавливаем сессию…",
    offlineBanner: "Офлайн — показаны кэшированные диалоги.",
    voiceButtonTooltip: "Удерживайте для голосового ввода",
    voiceButtonOffline: "Недоступно офлайн",
    voiceButtonRecording: "Отпустите, чтобы завершить",
    voiceButtonIdle: "Удерживать и говорить",
    playbackPrefix: "Озвучка: ",
    playbackSettingsLabel: "Открыть настройки озвучки",
    sendingLabel: "Отправка…",
    sendLabel: "Отправить",
  },
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
  const copyLocale = toCopyLocale(locale);
  const copy = CHAT_COPY[copyLocale];
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
      : copy.noSpecialties;
  const languagesLabel =
    recommendation.languages.length > 0
      ? recommendation.languages.join(" / ")
      : copy.noLanguages;
  const priceLabel = `${recommendation.price} ${recommendation.currency}`;
  const matchLabel = copy.matchLabel;

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
          {copy.focusLabel}
        </Text>
        <Text style={styles.metaValue}>{specialtiesLabel}</Text>
      </View>
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>
          {copy.languageLabel}
        </Text>
        <Text style={styles.metaValue}>{languagesLabel}</Text>
      </View>
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>
          {copy.feeLabel}
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
  copyLocale: CopyLocale,
): string {
  const copy = CHAT_COPY[copyLocale];
  if (isOffline) {
    return copy.voiceUnavailable;
  }
  if (isTranscribing) {
    return copy.voiceTranscribing;
  }
  if (isRecording) {
    return copy.voiceRecording;
  }
  return copy.voiceIdle;
}

export function ChatScreen({
  onNavigateBack,
  onOpenSettings,
}: ChatScreenProps) {
  const theme = useTheme();
  const switchColors = useMemo(() => getAcademicSwitchColors(theme), [theme]);
  const { tokens, userId } = useAuth();
  const { locale } = useLocale();
  const cacheMarkedRef = useRef(false);
  const screenVisibleRef = useRef(false);
  const firstResponseRef = useRef(false);
  const listRef = useRef<FlatList<MessageWithId>>(null);
  const insets = useSafeAreaInsets();
  const resolvedLocale = useMemo(() => locale ?? "zh-CN", [locale]);
  const copyLocale = toCopyLocale(resolvedLocale);
  const copy = CHAT_COPY[copyLocale];
  const isZhLocale = copyLocale === "zh";
  const {
    supported: voiceSupported,
    isRecording: isVoiceRecording,
    isTranscribing: isVoiceTranscribing,
    error: voiceError,
    start: startVoiceInput,
    stop: stopVoiceInput,
    cancel: cancelVoiceInput,
    clearError: clearVoiceError,
  } = useVoiceInput(resolvedLocale, tokens?.accessToken ?? null);
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
    ? copy.voicePlaybackLoading
    : isVoicePlaybackEnabled
      ? copy.voicePlaybackEnabled
      : copy.voicePlaybackDisabled;
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
          flexWrap: "wrap",
          gap: theme.spacing.sm,
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
          flexShrink: 1,
          flexGrow: 1,
          minWidth: 0,
        },
        headerRight: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
          justifyContent: "flex-end",
          flexShrink: 1,
          flexGrow: 1,
          minWidth: 0,
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
          flexShrink: 1,
          minWidth: 0,
        },
        headerMeta: {
          fontSize: 12,
          letterSpacing: 0.6,
          color: theme.colors.textSecondary,
          flexShrink: 1,
          minWidth: 0,
          textAlign: "right",
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
        composerContent: {
          gap: theme.spacing.sm,
        },
        composerButtons: {
          flexDirection: "row",
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
      locale: resolvedLocale,
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
    resolvedLocale,
  ]);

  useEffect(() => {
    if (!isOffline && error === copy.offlineSendError) {
      setError(null);
    }
  }, [copy.offlineSendError, error, isOffline]);

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
      setError(copy.offlineSendError);
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
        locale: resolvedLocale,
      });
      setSessionId(response.sessionId);
      const assistantMessage: MessageWithId = {
        id: `${Date.now()}-assistant`,
        role: response.reply.role,
        content: response.reply.content,
        createdAt: response.reply.createdAt,
      };
      appendMessage(assistantMessage);
      const playbackLocale = response.resolvedLocale ?? resolvedLocale;
      speakVoiceResponse({
        text: assistantMessage.content,
        locale: playbackLocale,
      });
      setRecommendations(
        normalizeTherapistRecommendations(response.recommendations),
      );
      setMemoryHighlights(response.memoryHighlights);
      if (!firstResponseRef.current) {
        markStartupEvent("chat-first-response");
        firstResponseRef.current = true;
      }
    } catch (err) {
      console.warn("Failed to send chat message", err);
      setError(
        err instanceof Error ? err.message : copy.sendErrorFallback,
      );
    } finally {
      setSending(false);
    }
  }, [
    tokens,
    userId,
    inputValue,
    sessionId,
    resolvedLocale,
    isOffline,
    appendMessage,
    speakVoiceResponse,
    copy.offlineSendError,
    copy.sendErrorFallback,
  ]);

  const sendDisabled = isSending || isOffline || inputValue.trim().length === 0;
  const { promptText, quoteText, quoteAttribution } = useMemo(() => {
    const localeKey = resolvePromptLocale(resolvedLocale);
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
  }, [resolvedLocale]);
  const recommendationIntro = copy.recommendationIntro;
  const overflowTitle = copy.overflowTitle;
  const overflowSettingsLabel = copy.overflowSettingsLabel;
  const overflowSettingsHint = copy.overflowSettingsHint;
  const composerPlaceholder = copy.composerPlaceholder;
  const modalTitle = copy.modalTitle;
  const modalEnableLabel = copy.modalEnableLabel;
  const modalRateLabel = copy.modalRateLabel;
  const modalPitchLabel = copy.modalPitchLabel;
  const modalHintLabel = copy.modalHintLabel;
  const modalDoneLabel = copy.modalDoneLabel;
  const renderListHeader = useCallback(() => {
    return (
      <View style={styles.listHeader}>
        <BlurView
          intensity={GLASS_INTENSITY + 5}
          tint="light"
          style={styles.promptCard}
        >
          <Text style={styles.promptLabel}>
            {copy.promptLabel}
          </Text>
          <Text style={styles.promptText}>{promptText}</Text>
          <Text style={styles.quoteText}>{`“${quoteText}”`}</Text>
          <Text style={styles.quoteAttribution}>{quoteAttribution}</Text>
        </BlurView>
        {recommendations.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {copy.recommendationsTitle}
            </Text>
            <Text style={styles.sectionSubtitle}>{recommendationIntro}</Text>
            {recommendations.map((recommendation, index) => (
              <View
                key={recommendation.id}
                style={styles.recommendationWrapper}
              >
                <Text style={styles.recommendationLead}>
                  {String.fromCharCode(65 + index)}.{" "}
                  {recommendation.reason || copy.recommendationFallback}
                </Text>
                <RecommendationCard
                  recommendation={recommendation}
                  locale={resolvedLocale}
                />
              </View>
            ))}
          </View>
        )}
        {memoryHighlights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {copy.highlightsTitle}
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
  }, [styles, promptText, quoteText, quoteAttribution, recommendations, memoryHighlights, recommendationIntro, copy]);
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
              accessibilityLabel={copy.backLabel}
              style={styles.backButton}
              onPress={() => {
                Haptics.selectionAsync().catch(() => undefined);
                onNavigateBack();
              }}
            >
              <Text style={styles.backIcon}>←</Text>
            </Pressable>
          )}
          <Text style={styles.headerTitle} numberOfLines={1}>
            {copy.headerTitle}
          </Text>
        </View>
        <View style={styles.headerRight}>
          <Text style={styles.headerMeta} numberOfLines={1}>
            {copy.headerMeta}
          </Text>
          {onOpenSettings && (
            <Pressable
              android_ripple={androidRipple}
              accessibilityRole="button"
              accessibilityLabel={copy.overflowAria}
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
            {copy.restoringLabel}
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
          {copy.offlineBanner}
        </Text>
      )}

      <View style={styles.composerShell}>
        <BlurView
          intensity={GLASS_INTENSITY + 5}
          tint="light"
          style={[styles.composer, { paddingBottom: composerPadding }]}
        >
          <View style={styles.composerContent}>
            <TextInput
              placeholder={composerPlaceholder}
              placeholderTextColor={theme.colors.textSecondary}
              value={inputValue}
              onChangeText={handleInputChange}
              style={styles.input}
              editable={!isSending && !isVoiceRecording && !isVoiceTranscribing}
              multiline
            />
            <View style={styles.composerButtons}>
              {voiceSupported && (
                <View style={{ flex: 1, minWidth: 0, gap: theme.spacing.xs }}>
                  <Pressable
                    android_ripple={androidRipple}
                    accessibilityRole="button"
                    accessibilityLabel={copy.voiceButtonTooltip}
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
                        ? copy.voiceButtonOffline
                        : isVoiceRecording
                          ? copy.voiceButtonRecording
                          : copy.voiceButtonIdle}
                    </Text>
                  </Pressable>
                  <View style={styles.voiceStatusRow}>
                    {isVoiceTranscribing && (
                      <ActivityIndicator size="small" color={theme.colors.primary} />
                    )}
                    <Text style={styles.voiceStatusText}>
                      {resolveVoiceStatusLabel(
                        isVoiceRecording,
                        isVoiceTranscribing,
                        isOffline,
                        copyLocale,
                      )}
                    </Text>
                  </View>
                  <Text style={styles.voiceModeStatus}>
                    {`${copy.playbackPrefix}${voicePlaybackStateLabel}`}
                  </Text>
                </View>
              )}
              {voiceSupported && (
                <Pressable
                  android_ripple={androidRipple}
                  accessibilityRole="button"
                  accessibilityLabel={copy.playbackSettingsLabel}
                  onPress={() => setVoiceSettingsVisible(true)}
                  style={styles.voiceArrowButton}
                >
                  <Text style={styles.voiceArrowIcon}>↢</Text>
                </Pressable>
              )}
              <Pressable
                android_ripple={androidRipple}
                onPress={handleSend}
                style={[styles.sendButton, { opacity: sendDisabled ? 0.5 : 1 }]}
                disabled={sendDisabled}
              >
                <Text style={styles.sendLabel}>
                  {isSending ? copy.sendingLabel : copy.sendLabel}
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
