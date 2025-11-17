import { VOICE_PITCH_PRESETS, VOICE_RATE_PRESETS } from "@constants/voice";
import { useAuth } from "@context/AuthContext";
import { useVoiceSettings } from "@context/VoiceSettingsContext";
import { BlurView } from "expo-blur";
import * as Localization from "expo-localization";
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
import { useTheme } from "../theme/ThemeProvider";

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

const GLASS_INTENSITY = Platform.OS === "ios" ? 130 : 145;

export function SettingsScreen() {
  const theme = useTheme();
  const { userId, logout } = useAuth();
  const {
    enabled: voiceEnabled,
    setEnabled: setVoiceEnabled,
    rate: voiceRate,
    pitch: voicePitch,
    setRate: setVoiceRate,
    setPitch: setVoicePitch,
    reset: resetVoiceSettings,
  } = useVoiceSettings();
  const locale = Localization.locale ?? "zh-CN";
  const isZh = locale.startsWith("zh");
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
      }),
    [theme],
  );

  const rateLabel = isZh ? "语速" : "Voice rate";
  const pitchLabel = isZh ? "音调" : "Vocal tone";
  const playbackLabel = isZh ? "语音播报" : "Voice playback";
  const logoutLabel = isZh ? "退出登录" : "Sign out";
  const accountSubtitle = isZh
    ? "保持账号安全，并重新登录以刷新访问令牌。"
    : "Keep your account secure and re-authenticate when needed.";
  const voiceSubtitle = isZh
    ? "调整语音播报参数，便于在安静或私密场景中使用。"
    : "Tune voice playback to suit quieter or more private listening sessions.";
  const ideaTitle = isZh ? "设置入口脑暴" : "Settings placement brainstorming";
  const voiceResetLabel = isZh
    ? "恢复默认播放参数"
    : "Reset playback defaults";
  const voiceResetFeedbackText = isZh
    ? "语音播放参数已恢复默认值。"
    : "Voice playback defaults restored.";
  const storageTitle = isZh ? "数据与存储" : "Data & storage";
  const storageSubtitle = isZh
    ? "当缓存偏离当下状态时，可手动清除本地数据。"
    : "Flush local caches if they drift from your current state.";
  const cacheLabel = isZh ? "聊天缓存" : "Chat cache";
  const cacheDescription = isZh
    ? "清理后将移除本地对话内容、推荐和记忆概览。"
    : "Clearing removes local transcripts, recommendations, and memory cards.";
  const clearButtonLabel = isZh ? "清空缓存" : "Clear cache";
  const clearingLabel = isZh ? "清理中…" : "Clearing…";
  const cacheSuccessMessage = isZh
    ? "已清除本地对话缓存与推荐。"
    : "Cleared cached chat transcripts and recommendations.";
  const cacheErrorMessage = isZh
    ? "清理缓存时出现异常，请稍后再试。"
    : "Unable to clear cache right now. Please retry shortly.";
  const cacheNeedsAccountMessage = isZh
    ? "需要有效的账号才能清理缓存。"
    : "You need an active session to clear cached data.";
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
        <Text style={styles.cardTitle}>{isZh ? "账号" : "Account"}</Text>
        <Text style={styles.cardSubtitle}>
          {accountSubtitle} {userId ? `ID：${userId}` : ""}
        </Text>
        <Pressable style={styles.outlineButton} onPress={handleLogout}>
          <Text style={styles.outlineLabel}>{logoutLabel}</Text>
        </Pressable>
      </BlurView>

      <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.card}>
        <Text style={styles.cardTitle}>{playbackLabel}</Text>
        <Text style={styles.cardSubtitle}>{voiceSubtitle}</Text>
        <View style={styles.row}>
          <Text style={styles.sectionLabel}>
            {isZh ? "启用语音播报" : "Enable playback"}
          </Text>
          <Switch value={voiceEnabled} onValueChange={handleVoiceEnabledChange} />
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
              {isZh ? idea.zh : idea.en}
            </Text>
          ))}
        </View>
      </BlurView>
    </ScrollView>
  );
}
