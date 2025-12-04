import { useAuth } from "@context/AuthContext";
import { useLocale, LOCALE_KEYS } from "@context/LocaleContext";
import { useTheme } from "@theme/ThemeProvider";
import { getAcademicSwitchColors } from "@theme/switchColors";
import { BlurView } from "expo-blur";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Platform,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

import { useTherapistDirectory } from "../hooks/useTherapistDirectory";
import { loadChatState } from "../services/chatCache";
import { normalizeTherapistRecommendations } from "../services/recommendations";
import { loadTherapistDetail } from "../services/therapists";
import type {
  TherapistDetail,
  TherapistRecommendation,
  TherapistSummary,
} from "../types/therapists";
import { translateBatch } from "@services/translation";
import { toCopyLocale, type CopyLocale } from "@utils/locale";

type DetailState =
  | { status: "idle"; detail: null; error: null }
  | { status: "loading"; detail: null; error: null }
  | { status: "loaded"; detail: TherapistDetail; error: null }
  | { status: "error"; detail: null; error: string };

type DirectoryCopy = (typeof DIRECTORY_COPY)[CopyLocale];

const DIRECTORY_COPY = {
  zh: {
    cardBadge: "推荐",
    noSpecialties: "未提供擅长领域",
    noLanguages: "未提供可用语言",
    pricePrefix: "每次",
    searchPlaceholder: "搜索姓名、流派或关键词",
    recommendationTitle: "AI 推荐顾问",
    recommendationSubtitle: "根据你与 AI 的对话生成，供你优先考虑。",
    recommendationLead: "根据你与 AI 的对话，我们推荐以下三位顾问。",
    recommendationFallback: "与当前主题匹配。",
    headerTitle: "顾问目录",
    headerSubtitle: "根据主题、语言和价格快速筛选合适的心理顾问。",
    sourceLive: "实时数据",
    sourceFallback: "离线示例数据",
    resetFilters: "重置筛选",
    filterFocus: "关注主题",
    filterFocusEmpty: "暂无主题信息",
    filterLanguages: "支持语言",
    filterLanguagesEmpty: "暂无语言信息",
    filterMinPrice: "价格下限（每次）",
    filterMaxPrice: "价格上限（每次）",
    minPricePrefix: "最低",
    maxPricePrefix: "最高",
    priceUnlimited: "不限",
    onlyRecommended: "只看推荐顾问",
    emptyState: "没有符合条件的顾问，请调整筛选条件。",
    detailEmpty: "选择顾问即可查看详细介绍。",
    detailLoading: "正在载入顾问详情…",
    detailError: "无法加载顾问详情，请稍后再试。",
    biographyFallback: "暂无详细介绍。",
    recommendationReasonPrefix: "推荐理由：",
    availabilityLabel: "可预约时间",
    availabilityEmpty: "暂无排期信息。",
  },
  en: {
    cardBadge: "Recommended",
    noSpecialties: "No specialties provided",
    noLanguages: "Languages not provided",
    pricePrefix: "Per session",
    searchPlaceholder: "Search by name, modality, or keyword",
    recommendationTitle: "AI recommendations",
    recommendationSubtitle: "Rooted in your AI conversations so you can triage faster.",
    recommendationLead: "Based on your conversations with the AI, we recommend the following three therapists.",
    recommendationFallback: "Aligned with your recent topic.",
    headerTitle: "Therapist directory",
    headerSubtitle: "Filter by topic, language, and price to find the right fit.",
    sourceLive: "Live data",
    sourceFallback: "Offline sample data",
    resetFilters: "Reset filters",
    filterFocus: "Focus areas",
    filterFocusEmpty: "No topic information",
    filterLanguages: "Supported languages",
    filterLanguagesEmpty: "No language information",
    filterMinPrice: "Minimum price (per session)",
    filterMaxPrice: "Maximum price (per session)",
    minPricePrefix: "Min",
    maxPricePrefix: "Max",
    priceUnlimited: "No limit",
    onlyRecommended: "Show recommended only",
    emptyState: "No therapists match. Adjust your filters.",
    detailEmpty: "Select a therapist to view details.",
    detailLoading: "Loading therapist details…",
    detailError: "Unable to load therapist details. Please try again.",
    biographyFallback: "No biography provided.",
    recommendationReasonPrefix: "Reason: ",
    availabilityLabel: "Available slots",
    availabilityEmpty: "No availability provided.",
  },
  ru: {
    cardBadge: "Рекомендовано",
    noSpecialties: "Специализация не указана",
    noLanguages: "Языки не указаны",
    pricePrefix: "За сессию",
    searchPlaceholder: "Поиск по имени, подходу или ключевым словам",
    recommendationTitle: "Рекомендации ИИ",
    recommendationSubtitle: "Основаны на ваших разговорах с ИИ, чтобы быстрее выбрать.",
    recommendationLead: "По вашим разговорам с ИИ рекомендуем следующих трёх терапевтов.",
    recommendationFallback: "Подходит под последние темы.",
    headerTitle: "Каталог терапевтов",
    headerSubtitle: "Фильтруйте по теме, языку и цене, чтобы найти подходящего специалиста.",
    sourceLive: "Живые данные",
    sourceFallback: "Офлайн-пример данных",
    resetFilters: "Сбросить фильтры",
    filterFocus: "Темы",
    filterFocusEmpty: "Нет информации о темах",
    filterLanguages: "Поддерживаемые языки",
    filterLanguagesEmpty: "Нет информации о языках",
    filterMinPrice: "Минимальная цена (за сессию)",
    filterMaxPrice: "Максимальная цена (за сессию)",
    minPricePrefix: "Мин",
    maxPricePrefix: "Макс",
    priceUnlimited: "Без ограничений",
    onlyRecommended: "Только рекомендованные",
    emptyState: "Нет совпадений. Измените фильтры.",
    detailEmpty: "Выберите терапевта, чтобы увидеть детали.",
    detailLoading: "Загружаем данные терапевта…",
    detailError: "Не удалось загрузить данные. Попробуйте позже.",
    biographyFallback: "Биография не указана.",
    recommendationReasonPrefix: "Причина: ",
    availabilityLabel: "Доступное время",
    availabilityEmpty: "Нет данных о расписании.",
  },
} as const;

type TherapistCardProps = {
  therapist: TherapistSummary;
  active: boolean;
  onPress: (therapist: TherapistSummary) => void;
  copy: DirectoryCopy;
};

const GLASS_INTENSITY = Platform.OS === "ios" ? 145 : 165;

function TherapistCard({ therapist, active, onPress, copy }: TherapistCardProps) {
  const theme = useTheme();

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: active
            ? theme.colors.textPrimary
            : theme.colors.glassBorder,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
          backgroundColor: theme.colors.glassOverlay,
        },
        header: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: theme.spacing.xs,
        },
        name: {
          fontSize: 16,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        title: {
          fontSize: 14,
          color: theme.colors.textSecondary,
        },
        badge: {
          backgroundColor: "transparent",
          borderWidth: 1,
          borderColor: theme.colors.primary,
          color: theme.colors.primary,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.8,
          fontSize: 12,
          fontWeight: "600",
        },
        caption: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
      }),
    [active, theme],
  );

  return (
    <Pressable onPress={() => onPress(therapist)} style={styles.container}>
      <View style={styles.header}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.name}>{therapist.name}</Text>
          <Text style={styles.title}>{therapist.title}</Text>
        </View>
        {therapist.recommended && (
          <Text style={styles.badge}>{copy.cardBadge}</Text>
        )}
      </View>
      <Text style={styles.caption}>
        {therapist.specialties.join(" · ") || copy.noSpecialties}
      </Text>
      <Text style={styles.caption}>
        {therapist.languages.join(" / ") || copy.noLanguages}
      </Text>
      <Text style={styles.caption}>
        {copy.pricePrefix} {therapist.price} {therapist.currency}
      </Text>
    </Pressable>
  );
}

type FilterChipProps = {
  label: string;
  active: boolean;
  onPress: () => void;
};

function FilterChip({ label, active, onPress }: FilterChipProps) {
  const theme = useTheme();

  const styles = useMemo(
    () =>
      StyleSheet.create({
        chip: {
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: active
            ? theme.colors.textPrimary
            : theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs * 0.75,
          backgroundColor: "transparent",
        },
        text: {
          color: active ? theme.colors.textPrimary : theme.colors.textSecondary,
          fontSize: 12,
          fontWeight: active ? "600" : "500",
        },
      }),
    [active, theme],
  );

  return (
    <Pressable onPress={onPress} style={styles.chip}>
      <Text style={styles.text}>{label}</Text>
    </Pressable>
  );
}

function renderAvailabilitySlot(slot: string, locale: string): string {
  const parsed = new Date(slot);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleString(locale, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return slot;
}

export function TherapistDirectoryScreen() {
  const { locale } = useLocale();
  const resolvedLocale = locale ?? LOCALE_KEYS.default;
  const copyLocale = toCopyLocale(resolvedLocale);
  const copy = DIRECTORY_COPY[copyLocale];
  const theme = useTheme();
  const switchColors = useMemo(() => getAcademicSwitchColors(theme), [theme]);
  const { userId } = useAuth();
  const flatListRef = useRef<FlatList<TherapistSummary>>(null);
  const {
    therapists,
    filtered: filteredByFilters,
    filters,
    setFilters,
    resetFilters,
    specialties,
    languages,
    minPrice,
    maxPrice,
    source,
    isLoading,
    isRefreshing,
    reload,
    error,
  } = useTherapistDirectory(resolvedLocale);

  const [searchQuery, setSearchQuery] = useState("");
  const [cachedRecommendations, setCachedRecommendations] = useState<
    TherapistRecommendation[]
  >([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailState, setDetailState] = useState<DetailState>({
    status: "idle",
    detail: null,
    error: null,
  });
  const [specialtyLabels, setSpecialtyLabels] = useState<Record<string, string>>(
    {},
  );
  const [languageLabels, setLanguageLabels] = useState<Record<string, string>>(
    {},
  );
  const lastSpecialtyKeyRef = useRef<string>("");
  const lastLanguageKeyRef = useRef<string>("");
  useEffect(() => {
    if (!userId) {
      setCachedRecommendations([]);
      return;
    }
    let cancelled = false;
    loadChatState(userId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        const normalized = normalizeTherapistRecommendations(
          payload?.recommendations?.slice(0, 3),
        );
        setCachedRecommendations(normalized);
      })
      .catch(() => {
        if (!cancelled) {
          setCachedRecommendations([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    const key = `${copyLocale}|${specialties.join("|")}`;
    if (specialties.length === 0 || copyLocale === "en") {
      if (lastSpecialtyKeyRef.current !== "") {
        lastSpecialtyKeyRef.current = "";
      }
      if (Object.keys(specialtyLabels).length > 0) {
        setSpecialtyLabels({});
      }
      return;
    }
    if (key === lastSpecialtyKeyRef.current) {
      return;
    }
    lastSpecialtyKeyRef.current = key;
    let cancelled = false;
    const entries = specialties.map((text) => ({ key: text, text }));
    translateBatch({
      targetLocale: resolvedLocale,
      sourceLocale: "en-US",
      namespace: "mobile.therapist-directory.specialties",
      entries,
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        const mapped: Record<string, string> = {};
        entries.forEach((entry) => {
          mapped[entry.key] =
            (response.translations?.[entry.key] as string | undefined) ??
            entry.text;
        });
        setSpecialtyLabels(mapped);
      })
      .catch((err) => {
        console.warn("[TherapistDirectory] Failed to translate specialties", err);
        if (!cancelled) {
          setSpecialtyLabels({});
        }
      });
    return () => {
      cancelled = true;
    };
  }, [copyLocale, resolvedLocale, specialties]);

  useEffect(() => {
    const key = `${copyLocale}|${languages.join("|")}`;
    if (languages.length === 0 || copyLocale === "en") {
      if (lastLanguageKeyRef.current !== "") {
        lastLanguageKeyRef.current = "";
      }
      if (Object.keys(languageLabels).length > 0) {
        setLanguageLabels({});
      }
      return;
    }
    if (key === lastLanguageKeyRef.current) {
      return;
    }
    lastLanguageKeyRef.current = key;
    let cancelled = false;
    const entries = languages.map((text) => ({ key: text, text }));
    translateBatch({
      targetLocale: resolvedLocale,
      sourceLocale: "en-US",
      namespace: "mobile.therapist-directory.languages",
      entries,
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        const mapped: Record<string, string> = {};
        entries.forEach((entry) => {
          mapped[entry.key] =
            (response.translations?.[entry.key] as string | undefined) ??
            entry.text;
        });
        setLanguageLabels(mapped);
      })
      .catch((err) => {
        console.warn("[TherapistDirectory] Failed to translate languages", err);
        if (!cancelled) {
          setLanguageLabels({});
        }
      });
    return () => {
      cancelled = true;
    };
  }, [copyLocale, resolvedLocale, languages]);

  const filtered = useMemo(() => {
    const base = filteredByFilters;
    const term = searchQuery.trim().toLowerCase();
    if (!term) {
      return base;
    }
    return base.filter((therapist) => {
      const haystack = [
        therapist.name,
        therapist.title,
        therapist.specialties.join(" "),
        therapist.languages.join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(term);
    });
  }, [filteredByFilters, searchQuery]);
  const searchPlaceholder = copy.searchPlaceholder;
  const recommendationTitle = copy.recommendationTitle;
  const recommendationSubtitle = copy.recommendationSubtitle;
  const recommendationLead = copy.recommendationLead;
  const recommendationSwatches = useMemo(
    () => theme.palette.recommendationSwatches,
    [theme.palette.recommendationSwatches],
  );

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    const stillVisible = filtered.some(
      (therapist) => therapist.id === selectedId,
    );
    if (!stillVisible) {
      setSelectedId(null);
      setDetailState({ status: "idle", detail: null, error: null });
    }
  }, [filtered, selectedId]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: "transparent",
          paddingHorizontal: theme.spacing.lg,
          paddingTop: theme.spacing.lg,
          paddingBottom: theme.spacing.xl,
          gap: theme.spacing.lg,
        },
        header: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        },
        title: {
          fontSize: 18,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        subtitle: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          marginTop: 4,
        },
        searchCard: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.md,
        },
        searchInput: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.lg,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs,
          color: theme.colors.textPrimary,
          backgroundColor: "rgba(255,255,255,0.4)",
        },
        recommendationCard: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
        },
        recommendationTitle: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        recommendationSubtitle: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          marginBottom: theme.spacing.xs,
        },
        recommendationList: {
          gap: theme.spacing.sm,
        },
        recommendationItem: {
          flexDirection: "row",
          alignItems: "flex-start",
          gap: theme.spacing.sm,
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          backgroundColor: "transparent",
          padding: theme.spacing.sm,
        },
        recommendationItemPressed: {
          opacity: 0.9,
        },
        recommendationLabel: {
          width: 28,
          height: 28,
          borderRadius: 14,
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          textAlign: "center",
          lineHeight: 28,
          fontWeight: "700",
          color: theme.colors.textPrimary,
          backgroundColor: theme.colors.glassOverlay,
        },
        recommendationName: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        recommendationReason: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        recommendationKeywordsRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs * 0.75,
        },
        recommendationKeyword: {
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.6,
          fontSize: 11,
          color: theme.colors.textSecondary,
        },
        recommendationMeta: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        badge: {
          backgroundColor: "rgba(74,144,121,0.15)",
          color: theme.colors.primary,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          fontSize: 12,
          fontWeight: "600",
        },
        filtersCard: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          padding: theme.spacing.md,
          gap: theme.spacing.md,
          backgroundColor: theme.colors.glassOverlay,
        },
        chipRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.sm,
        },
        filterLabel: {
          fontSize: 12,
          color: theme.colors.textSecondary,
          marginBottom: 4,
        },
        filterReset: {
          alignSelf: "flex-start",
          color: theme.colors.primary,
          fontSize: 12,
          fontWeight: "600",
        },
        input: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.md,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          color: theme.colors.textPrimary,
        },
        list: {
          flex: 1,
        },
        listContent: {
          paddingTop: theme.spacing.lg,
          gap: theme.spacing.md,
          paddingBottom: theme.spacing.lg,
        },
        emptyState: {
          textAlign: "center",
          color: theme.colors.textSecondary,
          marginTop: theme.spacing.lg,
        },
        detailCard: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          padding: theme.spacing.lg,
          gap: theme.spacing.sm,
          backgroundColor: theme.colors.glassOverlay,
        },
        detailTitle: {
          fontSize: 16,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        detailBody: {
          fontSize: 14,
          lineHeight: 20,
          color: theme.colors.textSecondary,
        },
        availabilityRow: {
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        },
        availabilityBadge: {
          borderRadius: theme.radius.pill,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.75,
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
      }),
    [theme],
  );

  const handleSelect = useCallback(
    async (therapist: TherapistSummary) => {
      setSelectedId(therapist.id);
      setDetailState({ status: "loading", detail: null, error: null });
      try {
        const detail = await loadTherapistDetail(therapist.id, "en-US");
        setDetailState({ status: "loaded", detail, error: null });
      } catch (err) {
        setDetailState({
          status: "error",
          detail: null,
          error:
            err instanceof Error ? err.message : copy.detailError,
        });
      }
    },
    [copy.detailError],
  );

  const handleResetFilters = useCallback(() => {
    resetFilters();
    setSelectedId(null);
    setDetailState({ status: "idle", detail: null, error: null });
  }, [resetFilters]);
  const focusTherapistById = useCallback(
    (therapistId: string) => {
      const summary =
        filtered.find((therapist) => therapist.id === therapistId) ??
        therapists.find((therapist) => therapist.id === therapistId);
      if (!summary) {
        return;
      }
      handleSelect(summary);
      const targetIndex = filtered.findIndex(
        (therapist) => therapist.id === therapistId,
      );
      if (targetIndex < 0) {
        return;
      }
      try {
        flatListRef.current?.scrollToIndex({
          index: targetIndex,
          animated: true,
          viewPosition: 0.05,
        });
      } catch (error) {
        console.warn(
          "[TherapistDirectory] Failed to scroll to recommendation",
          error,
        );
        flatListRef.current?.scrollToOffset({
          offset: 0,
          animated: true,
        });
      }
    },
    [filtered, therapists, handleSelect],
  );

  const renderTherapist = useCallback(
    ({ item }: { item: TherapistSummary }) => (
      <TherapistCard
        therapist={item}
        active={item.id === selectedId}
        onPress={handleSelect}
        copy={copy}
      />
    ),
    [copy, handleSelect, selectedId],
  );
  const listHeader = useMemo(
    () => (
      <View style={{ gap: theme.spacing.lg }}>
        <View>
          <Text style={styles.title}>{copy.headerTitle}</Text>
          <Text style={styles.subtitle}>{copy.headerSubtitle}</Text>
        </View>

        <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.searchCard}>
          <TextInput
            style={styles.searchInput}
            placeholder={searchPlaceholder}
            placeholderTextColor={theme.colors.textSecondary}
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
            autoCorrect={false}
            clearButtonMode="while-editing"
          />
        </BlurView>

        {cachedRecommendations.length > 0 && (
          <BlurView
            intensity={GLASS_INTENSITY + 5}
            tint="light"
            style={styles.recommendationCard}
          >
            <Text style={styles.recommendationTitle}>{recommendationTitle}</Text>
            <Text style={styles.recommendationSubtitle}>{recommendationLead}</Text>
            <Text style={styles.recommendationMeta}>{recommendationSubtitle}</Text>
            <View style={styles.recommendationList}>
              {cachedRecommendations.map((recommendation, index) => {
                const label = String.fromCharCode(65 + index);
                const backgroundColor =
                  recommendationSwatches[index % recommendationSwatches.length];
                const fallbackReason = copy.recommendationFallback;
                return (
                  <Pressable
                    key={recommendation.id}
                    style={({ pressed }) => [
                      styles.recommendationItem,
                      { backgroundColor },
                      pressed && styles.recommendationItemPressed,
                    ]}
                    android_ripple={{
                      color: "rgba(0,0,0,0.08)",
                      foreground: true,
                    }}
                    onPress={() => focusTherapistById(recommendation.id)}
                  >
                    <Text style={styles.recommendationLabel}>{label}</Text>
                    <View style={{ flex: 1, gap: 4 }}>
                      <Text style={styles.recommendationName}>
                        {`${label}. ${recommendation.name}`}
                      </Text>
                      <Text style={styles.recommendationReason}>
                        {recommendation.reason?.trim().length
                          ? recommendation.reason
                          : fallbackReason}
                      </Text>
                      {recommendation.matchedKeywords.length > 0 && (
                        <View style={styles.recommendationKeywordsRow}>
                          {recommendation.matchedKeywords.map((keyword) => (
                            <Text
                              key={`${recommendation.id}-${keyword}`}
                              style={styles.recommendationKeyword}
                            >
                              {keyword}
                            </Text>
                          ))}
                        </View>
                      )}
                    </View>
                  </Pressable>
                );
              })}
            </View>
          </BlurView>
        )}

        <BlurView intensity={GLASS_INTENSITY} tint="light" style={styles.filtersCard}>
          <View
            style={{
              flexDirection: "row",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            {source && (
              <Text style={styles.badge}>
                {source === "api" ? copy.sourceLive : copy.sourceFallback}
              </Text>
            )}
            <Pressable onPress={handleResetFilters}>
              <Text style={styles.filterReset}>{copy.resetFilters}</Text>
            </Pressable>
          </View>

          <View>
            <Text style={styles.filterLabel}>{copy.filterFocus}</Text>
            <View style={styles.chipRow}>
              {specialties.map((specialty) => (
                <FilterChip
                  key={specialty}
                  label={specialtyLabels[specialty] ?? specialty}
                  active={filters.specialty === specialty}
                  onPress={() =>
                    setFilters((prev) => ({
                      ...prev,
                      specialty: prev.specialty === specialty ? undefined : specialty,
                    }))
                  }
                />
              ))}
              {specialties.length === 0 && (
                <Text style={styles.subtitle}>{copy.filterFocusEmpty}</Text>
              )}
            </View>
          </View>

          <View>
            <Text style={styles.filterLabel}>{copy.filterLanguages}</Text>
            <View style={styles.chipRow}>
              {languages.map((language) => (
                <FilterChip
                  key={language}
                  label={languageLabels[language] ?? language}
                  active={filters.language === language}
                  onPress={() =>
                    setFilters((prev) => ({
                      ...prev,
                      language: prev.language === language ? undefined : language,
                    }))
                  }
                />
              ))}
              {languages.length === 0 && (
                <Text style={styles.subtitle}>{copy.filterLanguagesEmpty}</Text>
              )}
            </View>
          </View>

          <View>
            <Text style={styles.filterLabel}>{copy.filterMinPrice}</Text>
            <TextInput
              inputMode="numeric"
              keyboardType="number-pad"
              style={styles.input}
              placeholder={
                minPrice
                  ? `${copy.minPricePrefix} ${minPrice} ${
                      therapists[0]?.currency ?? "CNY"
                    }`
                  : copy.priceUnlimited
              }
              placeholderTextColor={theme.colors.textSecondary}
              value={filters.minPrice === undefined ? "" : String(filters.minPrice)}
              onChangeText={(value) => {
                setFilters((prev) => {
                  if (value.trim().length === 0) {
                    return { ...prev, minPrice: undefined };
                  }
                  const parsed = Number.parseInt(value, 10);
                  return {
                    ...prev,
                    minPrice: Number.isNaN(parsed) ? prev.minPrice : parsed,
                  };
                });
              }}
            />
          </View>

          <View>
            <Text style={styles.filterLabel}>{copy.filterMaxPrice}</Text>
            <TextInput
              inputMode="numeric"
              keyboardType="number-pad"
              style={styles.input}
              placeholder={
                maxPrice
                  ? `${copy.maxPricePrefix} ${maxPrice} ${
                      therapists[0]?.currency ?? "CNY"
                    }`
                  : copy.priceUnlimited
              }
              placeholderTextColor={theme.colors.textSecondary}
              value={filters.maxPrice === undefined ? "" : String(filters.maxPrice)}
              onChangeText={(value) => {
                setFilters((prev) => {
                  if (value.trim().length === 0) {
                    return { ...prev, maxPrice: undefined };
                  }
                  const parsed = Number.parseInt(value, 10);
                  return {
                    ...prev,
                    maxPrice: Number.isNaN(parsed) ? prev.maxPrice : parsed,
                  };
                });
              }}
            />
          </View>

          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Text style={styles.filterLabel}>{copy.onlyRecommended}</Text>
            <Switch
              value={Boolean(filters.recommendedOnly)}
              trackColor={{
                true: switchColors.trackTrue,
                false: switchColors.trackFalse,
              }}
              thumbColor={
                filters.recommendedOnly
                  ? switchColors.thumbTrue
                  : switchColors.thumbFalse
              }
              ios_backgroundColor={switchColors.iosFalse}
              onValueChange={(value) =>
                setFilters((prev) => ({
                  ...prev,
                  recommendedOnly: value,
                }))
              }
            />
          </View>
        </BlurView>
      </View>
    ),
    [
      cachedRecommendations,
      copy,
      focusTherapistById,
      languages,
      languageLabels,
      maxPrice,
      minPrice,
      filters,
      recommendationLead,
      recommendationSubtitle,
      recommendationTitle,
      recommendationSwatches,
      searchPlaceholder,
      searchQuery,
      setFilters,
      specialties,
      specialtyLabels,
      switchColors,
      theme.colors.textSecondary,
      theme.colors.primary,
      therapists,
    ],
  );

  const renderDetailCard = useCallback(() => {
    return (
      <BlurView intensity={GLASS_INTENSITY + 5} tint="light" style={styles.detailCard}>
        {detailState.status === "idle" && (
          <Text style={styles.subtitle}>{copy.detailEmpty}</Text>
        )}

        {detailState.status === "loading" && (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <ActivityIndicator size="small" color={theme.colors.primary} />
            <Text style={styles.subtitle}>{copy.detailLoading}</Text>
          </View>
        )}

        {detailState.status === "error" && (
          <Text style={[styles.subtitle, { color: theme.colors.danger }]}>
            {detailState.error}
          </Text>
        )}

        {detailState.status === "loaded" && detailState.detail && (
          <View style={{ gap: theme.spacing.sm }}>
            <Text style={styles.detailTitle}>{detailState.detail.name}</Text>
            <Text style={styles.detailBody}>{detailState.detail.title}</Text>
            <Text style={styles.detailBody}>
              {detailState.detail.biography || copy.biographyFallback}
            </Text>
            {detailState.detail.recommendationReason && (
              <Text
                style={[
                  styles.detailBody,
                  { color: theme.colors.primary, fontWeight: "600" },
                ]}
              >
                {copy.recommendationReasonPrefix}
                {detailState.detail.recommendationReason}
              </Text>
            )}
            <View style={{ gap: 4 }}>
              <Text style={styles.filterLabel}>{copy.availabilityLabel}</Text>
              <View style={styles.availabilityRow}>
                {detailState.detail.availability.length === 0 ? (
                  <Text style={styles.subtitle}>{copy.availabilityEmpty}</Text>
                ) : (
                  detailState.detail.availability.map((slot) => (
                    <Text key={slot} style={styles.availabilityBadge}>
                      {renderAvailabilitySlot(slot, resolvedLocale)}
                    </Text>
                  ))
                )}
              </View>
            </View>
          </View>
        )}

        {error && (
          <Text style={[styles.subtitle, { color: theme.colors.warning }]}>
            {error.message}
          </Text>
        )}
      </BlurView>
    );
  }, [copy, detailState, error, resolvedLocale, theme.colors.danger, theme.colors.primary, theme.colors.warning, theme.spacing.sm]);

  const emptyComponent = useMemo(
    () =>
      isLoading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} />
      ) : (
        <Text style={styles.emptyState}>{copy.emptyState}</Text>
      ),
    [copy.emptyState, isLoading, theme.colors.primary],
  );

  return (
    <View style={styles.container}>
      <FlatList
        ref={flatListRef}
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={renderTherapist}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        refreshing={isRefreshing}
        onRefresh={reload}
        ListHeaderComponent={listHeader}
        ListFooterComponent={renderDetailCard}
        ListEmptyComponent={emptyComponent}
      />
    </View>
  );
}
