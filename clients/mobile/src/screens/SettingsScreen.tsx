import { VOICE_PITCH_PRESETS, VOICE_RATE_PRESETS } from "@constants/voice";
import { useAuth } from "@context/AuthContext";
import { useLocale, LOCALE_KEYS } from "@context/LocaleContext";
import { useVoiceSettings } from "@context/VoiceSettingsContext";
import { useTheme } from "@theme/ThemeProvider";
import type { PaletteId } from "@theme/palettes";
import { getAcademicSwitchColors } from "@theme/switchColors";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";

import { recordAnalyticsEvent } from "../services/analytics";
import { clearChatState } from "../services/chatCache";
import { toCopyLocale, type CopyLocale } from "@utils/locale";

const SETTING_IDEAS = [
  {
    id: "tab",
    zh: "在底部导航栏提供专属“设置”标签（当前采用方案），让设置入口始终位于四象限之一。",
    en: "Reserve one of the bottom navigation slots for a dedicated Settings tab (the approach implemented now) so the entry stays persistent.",
  },
  {
    id: "journey-hub",
    zh: "在旅程页顶部加入“设置”字母链接，提供更学术化的文本入口，避免堆叠图标。",
    en: "Add a typographic Settings link near the Journey header to create an academic-feeling text entry without stacking icons.",
  },
  {
    id: "composer-chip",
    zh: "在对话输入框左上角植入细线条设置 Chip，结合笔记图标，既不遮挡箭头又保持即达性。",
    en: "Embed a thin outlined Settings chip above the chat composer with a notebook icon so it stays accessible without crowding the arrow.",
  },
] as const;

const GLASS_INTENSITY = Platform.OS === "ios" ? 140 : 155;
const SUPPORTED_LOCALES = [
  { code: "zh-CN", label: "简体中文" },
  { code: "en-US", label: "English" },
  { code: "zh-TW", label: "繁體中文" },
  { code: "ru-RU", label: "Русский" },
] as const;

const SETTINGS_COPY = {
  zh: {
    interfaceTitle: "界面语言",
    interfaceSubtitle: "选择用于聊天和界面的语言。",
    logoutLabel: "退出登录",
    accountTitle: "账号",
    accountSubtitle: "保持账号安全，并重新登录以刷新访问令牌。",
    paletteTitle: "界面配色",
    paletteSubtitle:
      "切换黄绿 / 粉绿 / 蓝绿渐变，与 Messenger Creation 参考保持一致。",
    paletteActiveBadge: "当前",
    playbackLabel: "语音播报",
    playbackToggleLabel: "启用语音播报",
    rateLabel: "语速",
    pitchLabel: "音调",
    voiceSubtitle: "调整语音播报参数，便于在安静或私密场景中使用。",
    ideaTitle: "设置入口脑暴",
    voiceResetLabel: "恢复默认播放参数",
    voiceResetFeedbackText: "语音播放参数已恢复默认值。",
    storageTitle: "数据与存储",
    storageSubtitle: "当缓存偏离当下状态时，可手动清除本地数据。",
    cacheLabel: "聊天缓存",
    cacheDescription: "清理后将移除本地对话内容、推荐和记忆概览。",
    clearButtonLabel: "清空缓存",
    clearingLabel: "清理中…",
    cacheSuccessMessage: "已清除本地对话缓存与推荐。",
    cacheErrorMessage: "清理缓存时出现异常，请稍后再试。",
    cacheNeedsAccountMessage: "需要有效的账号才能清理缓存。",
  },
  en: {
    interfaceTitle: "Interface language",
    interfaceSubtitle: "Choose the language used across chat and the UI.",
    logoutLabel: "Sign out",
    accountTitle: "Account",
    accountSubtitle: "Keep your account secure and re-authenticate when needed.",
    paletteTitle: "Interface palette",
    paletteSubtitle:
      "Toggle the yellow–green, pink–green, or blue–green gradients from the Messenger Creation reference.",
    paletteActiveBadge: "Active",
    playbackLabel: "Voice playback",
    playbackToggleLabel: "Enable playback",
    rateLabel: "Voice rate",
    pitchLabel: "Vocal tone",
    voiceSubtitle: "Tune voice playback to suit quieter or more private listening sessions.",
    ideaTitle: "Settings placement brainstorming",
    voiceResetLabel: "Reset playback defaults",
    voiceResetFeedbackText: "Voice playback defaults restored.",
    storageTitle: "Data & storage",
    storageSubtitle: "Flush local caches if they drift from your current state.",
    cacheLabel: "Chat cache",
    cacheDescription:
      "Clearing removes local transcripts, recommendations, and memory cards.",
    clearButtonLabel: "Clear cache",
    clearingLabel: "Clearing…",
    cacheSuccessMessage: "Cleared cached chat transcripts and recommendations.",
    cacheErrorMessage: "Unable to clear cache right now. Please retry shortly.",
    cacheNeedsAccountMessage: "You need an active session to clear cached data.",
  },
  ru: {
    interfaceTitle: "Язык интерфейса",
    interfaceSubtitle: "Выберите язык для чата и интерфейса.",
    logoutLabel: "Выйти",
    accountTitle: "Аккаунт",
    accountSubtitle: "Сохраняйте безопасность аккаунта и обновляйте токен при необходимости.",
    paletteTitle: "Цветовая палитра",
    paletteSubtitle:
      "Переключайте жёлто‑зелёный, розово‑зелёный или сине‑зелёный градиенты как в Messenger Creation.",
    paletteActiveBadge: "Активно",
    playbackLabel: "Озвучка",
    playbackToggleLabel: "Включить озвучку",
    rateLabel: "Скорость",
    pitchLabel: "Тон",
    voiceSubtitle: "Подстройте озвучку для тихих или приватных сценариев.",
    ideaTitle: "Идеи размещения настроек",
    voiceResetLabel: "Сбросить параметры озвучки",
    voiceResetFeedbackText: "Настройки озвучки восстановлены.",
    storageTitle: "Данные и хранилище",
    storageSubtitle: "Очищайте кеш, если состояние расходится с текущим.",
    cacheLabel: "Кэш чата",
    cacheDescription:
      "Очистка удалит локальные диалоги, рекомендации и карточки памяти.",
    clearButtonLabel: "Очистить кеш",
    clearingLabel: "Очистка…",
    cacheSuccessMessage: "Локальный кеш диалогов и рекомендаций очищен.",
    cacheErrorMessage: "Не удалось очистить кеш. Попробуйте позже.",
    cacheNeedsAccountMessage: "Нужна активная сессия, чтобы очистить кеш.",
  },
} as const;

type SettingsCopy = (typeof SETTINGS_COPY)[CopyLocale];

export function SettingsScreen() {
  const theme = useTheme();
  const switchColors = useMemo(() => getAcademicSwitchColors(theme), [theme]);
  const { userId, logout } = useAuth();
  const { locale, setLocale } = useLocale();
  const {
    enabled: voiceEnabled,
    setEnabled: setVoiceEnabled,
    rate: voiceRate,
    pitch: voicePitch,
    setRate: setVoiceRate,
    setPitch: setVoicePitch,
    reset: resetVoiceSettings,
  } = useVoiceSettings();
  const resolvedLocale = locale ?? LOCALE_KEYS.default;
  const copyLocale: CopyLocale = toCopyLocale(resolvedLocale);
  const copy: SettingsCopy = SETTINGS_COPY[copyLocale];
  const isZh = copyLocale === "zh";
  const [voiceFeedback, setVoiceFeedback] = useState<string | null>(null);
  const voiceFeedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isClearingCache, setIsClearingCache] = useState(false);
  const [cacheFeedback, setCacheFeedback] = useState<{
    tone: "success" | "error";
    message: string;
  } | null>(null);
  const cacheFeedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logSettingsEvent = useCallback(
    (eventType: string, properties?: Record<string, unknown>) => {
      recordAnalyticsEvent({
        eventType,
        userId: userId ?? undefined,
        funnelStage: "retention",
        properties,
      }).catch((error) => {
        console.warn("[Analytics] Failed to record settings event", error);
      });
    },
    [userId],
  );

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
        },
        scrollContent: {
          flexGrow: 1,
          gap: theme.spacing.lg,
          paddingBottom: theme.spacing.xl,
        },
        card: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          padding: theme.spacing.lg,
          backgroundColor: theme.colors.glassOverlay,
          gap: theme.spacing.md,
        },
        cardTitle: {
          fontSize: 18,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        cardSubtitle: {
          fontSize: 14,
          color: theme.colors.textSecondary,
          lineHeight: 20,
        },
        sectionLabel: {
          fontSize: 12,
          letterSpacing: 0.4,
          color: theme.colors.textSecondary,
        },
        outlineButton: {
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          borderRadius: theme.radius.md,
          paddingVertical: theme.spacing.sm,
          alignItems: "center",
        },
        outlineLabel: {
          fontWeight: "600",
          letterSpacing: 0.4,
          color: theme.colors.textPrimary,
        },
        dangerButton: {
          borderWidth: 1,
          borderColor: theme.colors.danger,
          borderRadius: theme.radius.md,
          paddingVertical: theme.spacing.sm,
          paddingHorizontal: theme.spacing.lg,
          alignItems: "center",
        },
        dangerLabel: {
          fontWeight: "600",
          letterSpacing: 0.4,
          color: theme.colors.danger,
        },
        row: {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        },
        chipRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.sm,
        },
        chip: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs * 0.75,
          backgroundColor: "transparent",
        },
        chipActive: {
          borderColor: theme.colors.primary,
        },
        chipLabel: {
          fontSize: 12,
          letterSpacing: 0.3,
          color: theme.colors.textSecondary,
        },
        chipLabelActive: {
          color: theme.colors.primary,
          fontWeight: "600",
        },
        ideaList: {
          gap: theme.spacing.sm,
        },
        ideaItem: {
          fontSize: 14,
          lineHeight: 20,
          color: theme.colors.textSecondary,
        },
        ideaBullet: {
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        statusText: {
          fontSize: 12,
          marginTop: theme.spacing.xs,
        },
        statusSuccess: {
          color: theme.colors.primary,
        },
        statusError: {
          color: theme.colors.danger,
        },
        paletteGrid: {
          gap: theme.spacing.md,
        },
        paletteOption: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.lg,
          padding: theme.spacing.md,
          backgroundColor: "rgba(255,255,255,0.32)",
          gap: theme.spacing.sm,
        },
        paletteOptionActive: {
          borderColor: theme.colors.textPrimary,
          backgroundColor: "rgba(255,255,255,0.5)",
        },
        palettePreview: {
          height: 56,
          borderRadius: theme.radius.md,
          overflow: "hidden",
        },
        paletteMeta: {
          gap: 2,
        },
        paletteLabel: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        paletteLabelActive: {
          letterSpacing: 0.5,
        },
        paletteDescription: {
          fontSize: 12,
          lineHeight: 18,
          color: theme.colors.textSecondary,
        },
        paletteSwatchRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.xs,
        },
        paletteSwatch: {
          width: 18,
          height: 18,
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: "rgba(0,0,0,0.05)",
        },
        paletteBadge: {
          marginLeft: "auto",
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.6,
        },
        paletteBadgeLabel: {
          fontSize: 11,
          fontWeight: "600",
          letterSpacing: 0.4,
          color: theme.colors.textPrimary,
        },
      }),
    [theme],
  );

  const rateLabel = copy.rateLabel;
  const pitchLabel = copy.pitchLabel;
  const playbackLabel = copy.playbackLabel;
  const logoutLabel = copy.logoutLabel;
  const paletteTitle = copy.paletteTitle;
  const paletteSubtitle = copy.paletteSubtitle;
  const paletteActiveBadge = copy.paletteActiveBadge;
  const { id: activePaletteId, options: paletteOptions, setPalette } =
    theme.palette;
  const accountSubtitle = copy.accountSubtitle;
  const voiceSubtitle = copy.voiceSubtitle;
  const ideaTitle = copy.ideaTitle;
  const voiceResetLabel = copy.voiceResetLabel;
  const voiceResetFeedbackText = copy.voiceResetFeedbackText;
  const storageTitle = copy.storageTitle;
  const storageSubtitle = copy.storageSubtitle;
  const cacheLabel = copy.cacheLabel;
  const cacheDescription = copy.cacheDescription;
  const clearButtonLabel = copy.clearButtonLabel;
  const clearingLabel = copy.clearingLabel;
  const cacheSuccessMessage = copy.cacheSuccessMessage;
  const cacheErrorMessage = copy.cacheErrorMessage;
  const cacheNeedsAccountMessage = copy.cacheNeedsAccountMessage;
  const scheduleVoiceFeedbackClear = useCallback(() => {
    if (voiceFeedbackTimer.current) {
      clearTimeout(voiceFeedbackTimer.current);
    }
    voiceFeedbackTimer.current = setTimeout(() => {
      setVoiceFeedback(null);
      voiceFeedbackTimer.current = null;
    }, 3200);
  }, []);

  const scheduleCacheFeedbackClear = useCallback(() => {
    if (cacheFeedbackTimer.current) {
      clearTimeout(cacheFeedbackTimer.current);
    }
    cacheFeedbackTimer.current = setTimeout(() => {
      setCacheFeedback(null);
      cacheFeedbackTimer.current = null;
    }, 3600);
  }, []);

  const handleResetVoice = useCallback(() => {
    resetVoiceSettings();
    setVoiceFeedback(voiceResetFeedbackText);
    scheduleVoiceFeedbackClear();
    logSettingsEvent("mobile_voice_settings_reset");
  }, [
    logSettingsEvent,
    resetVoiceSettings,
    scheduleVoiceFeedbackClear,
    voiceResetFeedbackText,
  ]);

  const handleClearCache = useCallback(async () => {
    if (!userId) {
      setCacheFeedback({ tone: "error", message: cacheNeedsAccountMessage });
      scheduleCacheFeedbackClear();
      logSettingsEvent("mobile_cache_clear_attempted", {
        status: "blocked_no_user",
      });
      return;
    }
    setIsClearingCache(true);
    setCacheFeedback(null);
    try {
      await clearChatState(userId);
      setCacheFeedback({ tone: "success", message: cacheSuccessMessage });
      logSettingsEvent("mobile_cache_clear_attempted", { status: "success" });
    } catch {
      setCacheFeedback({ tone: "error", message: cacheErrorMessage });
      logSettingsEvent("mobile_cache_clear_attempted", { status: "error" });
    } finally {
      setIsClearingCache(false);
      scheduleCacheFeedbackClear();
    }
  }, [
    cacheErrorMessage,
    cacheNeedsAccountMessage,
    cacheSuccessMessage,
    logSettingsEvent,
    scheduleCacheFeedbackClear,
    userId,
  ]);

  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  const handlePaletteSelect = useCallback(
    (paletteId: PaletteId) => {
      if (paletteId === activePaletteId) {
        return;
      }
      setPalette(paletteId);
      logSettingsEvent("mobile_palette_selected", { palette_id: paletteId });
    },
    [activePaletteId, logSettingsEvent, setPalette],
  );

  const handleVoiceEnabledChange = useCallback(
    (value: boolean) => {
      setVoiceEnabled(value);
      logSettingsEvent("mobile_voice_playback_toggled", {
        enabled: value,
      });
    },
    [logSettingsEvent, setVoiceEnabled],
  );

  const handleVoiceRateChange = useCallback(
    (presetId: string, value: number) => {
      if (Math.abs(voiceRate - value) < 0.01) {
        return;
      }
      setVoiceRate(value);
      logSettingsEvent("mobile_voice_rate_selected", {
        preset_id: presetId,
        rate: value,
      });
    },
    [logSettingsEvent, setVoiceRate, voiceRate],
  );

  const handleVoicePitchChange = useCallback(
    (presetId: string, value: number) => {
      if (Math.abs(voicePitch - value) < 0.01) {
        return;
      }
      setVoicePitch(value);
      logSettingsEvent("mobile_voice_pitch_selected", {
        preset_id: presetId,
        pitch: value,
      });
    },
    [logSettingsEvent, setVoicePitch, voicePitch],
  );

  useEffect(() => {
    return () => {
      if (voiceFeedbackTimer.current) {
        clearTimeout(voiceFeedbackTimer.current);
      }
      if (cacheFeedbackTimer.current) {
        clearTimeout(cacheFeedbackTimer.current);
      }
    };
  }, []);
  return (
    <ScrollView
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>
          {copy.interfaceTitle}
        </Text>
        <Text style={styles.cardSubtitle}>
          {copy.interfaceSubtitle}
        </Text>
        <View style={styles.chipRow}>
          {SUPPORTED_LOCALES.map((option) => {
            const active = resolvedLocale === option.code;
            return (
              <Pressable
                key={option.code}
                onPress={() => setLocale(option.code)}
                style={[styles.chip, active && styles.chipActive]}
              >
                <Text
                  style={[styles.chipLabel, active && styles.chipLabelActive]}
                >
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{copy.accountTitle}</Text>
        <Text style={styles.cardSubtitle}>
          {accountSubtitle} {userId ? `ID：${userId}` : ""}
        </Text>
        <Pressable style={styles.outlineButton} onPress={handleLogout}>
          <Text style={styles.outlineLabel}>{logoutLabel}</Text>
        </Pressable>
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{paletteTitle}</Text>
        <Text style={styles.cardSubtitle}>{paletteSubtitle}</Text>
        <View style={styles.paletteGrid}>
          {paletteOptions.map((option) => {
            const isActive = option.id === activePaletteId;
            const swatches = isActive
              ? theme.palette.recommendationSwatches
              : option.preview;
            return (
              <Pressable
                key={option.id}
                onPress={() => handlePaletteSelect(option.id)}
                style={[
                  styles.paletteOption,
                  isActive && styles.paletteOptionActive,
                ]}
              >
                <LinearGradient
                  colors={option.preview}
                  start={{ x: 0.5, y: 1 }}
                  end={{ x: 0.5, y: 0 }}
                  style={styles.palettePreview}
                />
                <View style={styles.paletteMeta}>
                  <Text
                    style={[
                      styles.paletteLabel,
                      isActive && styles.paletteLabelActive,
                    ]}
                  >
                    {isZh ? option.labelZh : option.labelEn}
                  </Text>
                  <Text style={styles.paletteDescription}>
                    {isZh ? option.descriptionZh : option.descriptionEn}
                  </Text>
                </View>
                <View style={styles.paletteSwatchRow}>
                  {swatches.map((color, index) => (
                    <View
                      key={`${option.id}-${index}`}
                      style={[styles.paletteSwatch, { backgroundColor: color }]}
                    />
                  ))}
                  {isActive && (
                    <View style={styles.paletteBadge}>
                      <Text style={styles.paletteBadgeLabel}>
                        {paletteActiveBadge}
                      </Text>
                    </View>
                  )}
                </View>
              </Pressable>
            );
          })}
        </View>
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{playbackLabel}</Text>
        <Text style={styles.cardSubtitle}>{voiceSubtitle}</Text>
        <View style={styles.row}>
          <Text style={styles.sectionLabel}>
            {copy.playbackToggleLabel}
          </Text>
          <Switch
            value={voiceEnabled}
            onValueChange={handleVoiceEnabledChange}
            trackColor={{
              true: switchColors.trackTrue,
              false: switchColors.trackFalse,
            }}
            thumbColor={
              voiceEnabled ? switchColors.thumbTrue : switchColors.thumbFalse
            }
            ios_backgroundColor={switchColors.iosFalse}
          />
        </View>

        <View>
          <Text style={styles.sectionLabel}>{rateLabel}</Text>
          <View style={styles.chipRow}>
            {VOICE_RATE_PRESETS.map((preset) => {
              const isActive = Math.abs(voiceRate - preset.value) < 0.01;
              return (
                <Pressable
                  key={preset.id}
                  onPress={() => handleVoiceRateChange(preset.id, preset.value)}
                  style={[styles.chip, isActive && styles.chipActive]}
                >
                  <Text
                    style={[
                      styles.chipLabel,
                      isActive && styles.chipLabelActive,
                    ]}
                  >
                    {isZh ? preset.labelZh : preset.labelEn}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View>
          <Text style={styles.sectionLabel}>{pitchLabel}</Text>
          <View style={styles.chipRow}>
            {VOICE_PITCH_PRESETS.map((preset) => {
              const isActive = Math.abs(voicePitch - preset.value) < 0.01;
              return (
                <Pressable
                  key={preset.id}
                  onPress={() => handleVoicePitchChange(preset.id, preset.value)}
                  style={[styles.chip, isActive && styles.chipActive]}
                >
                  <Text
                    style={[
                      styles.chipLabel,
                      isActive && styles.chipLabelActive,
                    ]}
                  >
                    {isZh ? preset.labelZh : preset.labelEn}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <Pressable style={styles.outlineButton} onPress={handleResetVoice}>
          <Text style={styles.outlineLabel}>{voiceResetLabel}</Text>
        </Pressable>
        {voiceFeedback && (
          <Text
            style={[styles.statusText, styles.statusSuccess]}
            accessibilityLiveRegion="polite"
          >
            {voiceFeedback}
          </Text>
        )}
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{storageTitle}</Text>
        <Text style={styles.cardSubtitle}>{storageSubtitle}</Text>
        <View style={{ gap: theme.spacing.xs }}>
          <View style={styles.row}>
            <View style={{ flex: 1, paddingRight: theme.spacing.sm }}>
              <Text style={styles.sectionLabel}>{cacheLabel}</Text>
              <Text style={styles.cardSubtitle}>{cacheDescription}</Text>
            </View>
            <Pressable
              style={[
                styles.dangerButton,
                isClearingCache && { opacity: 0.6 },
              ]}
              disabled={isClearingCache}
              onPress={handleClearCache}
            >
              <Text style={styles.dangerLabel}>
                {isClearingCache ? clearingLabel : clearButtonLabel}
              </Text>
            </Pressable>
          </View>
          {cacheFeedback && (
            <Text
              style={[
                styles.statusText,
                cacheFeedback.tone === "success"
                  ? styles.statusSuccess
                  : styles.statusError,
              ]}
              accessibilityLiveRegion="polite"
            >
              {cacheFeedback.message}
            </Text>
          )}
        </View>
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{ideaTitle}</Text>
        <View style={styles.ideaList}>
          {SETTING_IDEAS.map((idea) => (
            <Text key={idea.id} style={styles.ideaItem}>
              <Text style={styles.ideaBullet}>• </Text>
              {copyLocale === "zh" ? idea.zh : idea.en}
            </Text>
          ))}
        </View>
      </BlurView>
    </ScrollView>
  );
}
