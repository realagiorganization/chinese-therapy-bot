import { useJourneyReports } from "@hooks/useJourneyReports";
import { useLocale, LOCALE_KEYS } from "@context/LocaleContext";
import { useTheme } from "@theme/ThemeProvider";
import { toCopyLocale, type CopyLocale } from "@utils/locale";
import { useEffect, useMemo, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

function resolveLocale(locale: string | null | undefined): string {
  if (!locale) {
    return "zh-CN";
  }
  if (locale.toLowerCase().startsWith("en")) {
    return "en-US";
  }
  if (locale.toLowerCase().startsWith("zh")) {
    return "zh-CN";
  }
  return locale;
}

type DetailTab = "summary" | "transcript";

const JOURNEY_COPY = {
  zh: {
    title: "成长旅程",
    subtitle: "回顾每日亮点、每周主题和重要对话片段。",
    fallbackBadge: "使用示例数据",
    dailyTitle: "每日总结",
    dailyEmpty: "暂无总结，请稍后再试或继续与 MindWell 对话。",
    moodUp: (delta: number) => `情绪提升 +${delta}`,
    moodDown: (delta: number) => `情绪下降 ${delta}`,
    moodFlat: "情绪平稳",
    tabSummary: "摘要",
    tabTranscript: "对话片段",
    conversationEmpty: "暂无对话记录，继续与 MindWell 交流以丰富总结。",
    speakerUser: "你",
    speakerAssistant: "MindWell",
    weeklyTitle: "每周主题",
    weeklyEmpty: "暂无每周总结，完成更多会话后将自动生成。",
    actionItems: "行动建议",
  },
  en: {
    title: "Journey",
    subtitle: "Review daily highlights, weekly themes, and key conversation slices.",
    fallbackBadge: "Using sample data",
    dailyTitle: "Daily snapshots",
    dailyEmpty: "No daily summary yet. Try again or keep chatting with MindWell.",
    moodUp: (delta: number) => `Mood up +${delta}`,
    moodDown: (delta: number) => `Mood down ${delta}`,
    moodFlat: "Mood stable",
    tabSummary: "Summary",
    tabTranscript: "Conversation",
    conversationEmpty: "No conversation slices yet. Keep chatting to fill this.",
    speakerUser: "You",
    speakerAssistant: "MindWell",
    weeklyTitle: "Weekly themes",
    weeklyEmpty: "No weekly summary yet. We'll generate it after more sessions.",
    actionItems: "Action items",
  },
  ru: {
    title: "Прогресс",
    subtitle: "Смотрите ежедневные акценты, недельные темы и ключевые фрагменты диалогов.",
    fallbackBadge: "Пример данных",
    dailyTitle: "Ежедневные итоги",
    dailyEmpty: "Сводки пока нет. Попробуйте позже или продолжайте общение с MindWell.",
    moodUp: (delta: number) => `Настроение выросло +${delta}`,
    moodDown: (delta: number) => `Настроение снизилось ${delta}`,
    moodFlat: "Настроение стабильно",
    tabSummary: "Сводка",
    tabTranscript: "Диалоги",
    conversationEmpty: "Нет фрагментов. Продолжайте диалоги, чтобы они появились.",
    speakerUser: "Вы",
    speakerAssistant: "MindWell",
    weeklyTitle: "Недельные темы",
    weeklyEmpty: "Недельной сводки пока нет. Она появится после ещё нескольких сессий.",
    actionItems: "Рекомендации",
  },
} as const;

export function JourneyScreen() {
  const { locale } = useLocale();
  const resolvedLocale = resolveLocale(locale ?? LOCALE_KEYS.default);
  const copyLocale: CopyLocale = toCopyLocale(resolvedLocale);
  const copy = JOURNEY_COPY[copyLocale];
  const theme = useTheme();
  const { daily, weekly, conversationsByDate, isLoading, source, refresh } =
    useJourneyReports(resolvedLocale);

  const [selectedDailyId, setSelectedDailyId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("summary");

  useEffect(() => {
    if (daily.length > 0) {
      setSelectedDailyId((prev) => prev ?? daily[0].id);
    } else {
      setSelectedDailyId(null);
    }
  }, [daily]);

  useEffect(() => {
    setActiveTab("summary");
  }, [selectedDailyId]);

  const selectedDaily = useMemo(
    () => daily.find((report) => report.id === selectedDailyId) ?? null,
    [daily, selectedDailyId],
  );

  const conversationsForSelected = useMemo(() => {
    if (!selectedDaily) {
      return [];
    }
    const key = selectedDaily.parsedDate
      ? selectedDaily.parsedDate.toISOString().slice(0, 10)
      : selectedDaily.reportDate.slice(0, 10);
    return conversationsByDate.get(key) ?? [];
  }, [conversationsByDate, selectedDaily]);

  const formatShortDate = useMemo(
    () =>
      new Intl.DateTimeFormat(resolvedLocale, {
        month: "short",
        day: "numeric",
        weekday: "short",
      }),
    [resolvedLocale],
  );

  const formatLongDate = useMemo(
    () =>
      new Intl.DateTimeFormat(resolvedLocale, {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
      }),
    [resolvedLocale],
  );

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: theme.colors.surfaceBackground,
        },
        content: {
          paddingHorizontal: theme.spacing.lg,
          paddingVertical: theme.spacing.lg,
          gap: theme.spacing.lg,
        },
        section: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          backgroundColor: theme.colors.surfaceCard,
          padding: theme.spacing.lg,
          gap: theme.spacing.md,
        },
        headerRow: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        },
        title: {
          fontSize: 20,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        subtitle: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        fallbackBadge: {
          fontSize: 12,
          color: theme.colors.warning,
        },
        dailyList: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.sm,
        },
        dailyCard: {
          flexBasis: "48%",
          borderRadius: theme.radius.md,
          borderWidth: 1,
          padding: theme.spacing.md,
          backgroundColor: theme.colors.surfaceMuted,
          borderColor: theme.colors.borderSubtle,
          gap: theme.spacing.xs,
        },
        dailyCardActive: {
          borderColor: theme.colors.primary,
          backgroundColor: "rgba(37,99,235,0.08)",
        },
        dailyDate: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        dailyTitle: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        dailySpotlight: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        moodBadge: {
          alignSelf: "flex-start",
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.8,
          fontSize: 12,
          color: theme.colors.primary,
          backgroundColor: "rgba(37,99,235,0.1)",
        },
        tabRow: {
          flexDirection: "row",
          borderRadius: theme.radius.pill,
          backgroundColor: theme.colors.surfaceMuted,
          padding: 4,
          gap: 4,
        },
        tabButton: {
          flex: 1,
          borderRadius: theme.radius.pill,
          paddingVertical: theme.spacing.xs,
          alignItems: "center",
        },
        tabActive: {
          backgroundColor: theme.colors.surfaceCard,
          shadowColor: theme.colors.primary,
          shadowOpacity: 0.12,
          shadowRadius: 6,
          shadowOffset: { width: 0, height: 2 },
        },
        tabLabel: {
          fontSize: 13,
          color: theme.colors.textSecondary,
        },
        tabLabelActive: {
          color: theme.colors.primary,
          fontWeight: "600",
        },
        summaryText: {
          fontSize: 14,
          lineHeight: 20,
          color: theme.colors.textSecondary,
        },
        conversationBubble: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing.md,
          backgroundColor: theme.colors.surfaceMuted,
          marginBottom: theme.spacing.sm,
        },
        bubbleMeta: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          marginBottom: 4,
        },
        weeklyCard: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          backgroundColor: theme.colors.surfaceMuted,
          padding: theme.spacing.md,
          gap: theme.spacing.sm,
        },
        weeklyTitle: {
          fontSize: 16,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        chipRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        },
        chip: {
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          backgroundColor: "rgba(37,99,235,0.08)",
          color: theme.colors.primary,
          fontSize: 12,
        },
        emptyState: {
          fontSize: 14,
          color: theme.colors.textSecondary,
        },
      }),
    [theme],
  );

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refresh} />
        }
      >
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>{copy.title}</Text>
            <Text style={styles.subtitle}>{copy.subtitle}</Text>
          </View>
          {source === "fallback" && (
            <Text style={styles.fallbackBadge}>{copy.fallbackBadge}</Text>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.subtitle}>{copy.dailyTitle}</Text>
          {daily.length === 0 ? (
            <Text style={styles.emptyState}>
              {copy.dailyEmpty}
            </Text>
          ) : (
            <View style={styles.dailyList}>
              {daily.map((report) => {
                const isActive = report.id === selectedDailyId;
                const moodLabel =
                  report.moodDelta > 0
                    ? copy.moodUp(report.moodDelta)
                    : report.moodDelta < 0
                      ? copy.moodDown(report.moodDelta)
                      : copy.moodFlat;
                return (
                  <Pressable
                    key={report.id}
                    onPress={() => setSelectedDailyId(report.id)}
                    style={[
                      styles.dailyCard,
                      isActive && styles.dailyCardActive,
                    ]}
                  >
                    <Text style={styles.dailyDate}>
                      {report.parsedDate
                        ? formatShortDate.format(report.parsedDate)
                        : report.reportDate}
                    </Text>
                    <Text style={styles.dailyTitle}>{report.title}</Text>
                    <Text style={styles.dailySpotlight}>
                      {report.spotlight}
                    </Text>
                    <Text style={styles.moodBadge}>{moodLabel}</Text>
                  </Pressable>
                );
              })}
            </View>
          )}

          {selectedDaily && (
            <View style={{ gap: theme.spacing.md }}>
              <Text style={styles.subtitle}>
                {selectedDaily.parsedDate
                  ? formatLongDate.format(selectedDaily.parsedDate)
                  : selectedDaily.reportDate}
              </Text>
              <View style={styles.tabRow}>
                <Pressable
                  onPress={() => setActiveTab("summary")}
                  style={[
                    styles.tabButton,
                    activeTab === "summary" && styles.tabActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.tabLabel,
                      activeTab === "summary" && styles.tabLabelActive,
                    ]}
                  >
                    {copy.tabSummary}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => setActiveTab("transcript")}
                  style={[
                    styles.tabButton,
                    activeTab === "transcript" && styles.tabActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.tabLabel,
                      activeTab === "transcript" && styles.tabLabelActive,
                    ]}
                  >
                    {copy.tabTranscript}
                  </Text>
                </Pressable>
              </View>

              {activeTab === "summary" ? (
                <Text style={styles.summaryText}>{selectedDaily.summary}</Text>
              ) : conversationsForSelected.length === 0 ? (
                <Text style={styles.emptyState}>
                  {copy.conversationEmpty}
                </Text>
              ) : (
                conversationsForSelected.map((conversation) => (
                  <View key={conversation.sessionId} style={{ gap: 8 }}>
                    {conversation.messages.map((message) => {
                      const parsed = new Date(message.createdAt);
                      const timestamp = Number.isNaN(parsed.getTime())
                        ? message.createdAt
                        : formatShortDate.format(parsed);
                      return (
                        <View
                          key={message.messageId}
                          style={styles.conversationBubble}
                        >
                          <Text style={styles.bubbleMeta}>
                            {message.role === "user"
                              ? copy.speakerUser
                              : copy.speakerAssistant}{" "}
                            ·{" "}
                            {timestamp}
                          </Text>
                          <Text style={styles.summaryText}>
                            {message.content}
                          </Text>
                        </View>
                      );
                    })}
                  </View>
                ))
              )}
            </View>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.subtitle}>{copy.weeklyTitle}</Text>
          {weekly.length === 0 ? (
            <Text style={styles.emptyState}>
              {copy.weeklyEmpty}
            </Text>
          ) : (
            weekly.map((report) => (
              <View key={report.id} style={styles.weeklyCard}>
                <Text style={styles.weeklyTitle}>
                  {report.parsedWeekStart
                    ? formatLongDate.format(report.parsedWeekStart)
                    : report.weekStart}
                </Text>
                <View style={styles.chipRow}>
                  {report.themes.map((themeLabel) => (
                    <Text key={themeLabel} style={styles.chip}>
                      {themeLabel}
                    </Text>
                  ))}
                </View>
                <Text style={styles.summaryText}>{report.highlights}</Text>
                {report.actionItems.length > 0 && (
                  <View style={{ gap: 4 }}>
                    <Text style={styles.subtitle}>{copy.actionItems}</Text>
                    {report.actionItems.map((item) => (
                      <Text key={item} style={styles.summaryText}>
                        • {item}
                      </Text>
                    ))}
                  </View>
                )}
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </View>
  );
}
