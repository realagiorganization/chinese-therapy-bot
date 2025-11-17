import { useAuth } from "@context/AuthContext";
import { BlurView } from "expo-blur";
import * as Localization from "expo-localization";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
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
import { useTheme } from "../theme/ThemeProvider";
import type {
  TherapistDetail,
  TherapistRecommendation,
  TherapistSummary,
} from "../types/therapists";

type DetailState =
  | { status: "idle"; detail: null; error: null }
  | { status: "loading"; detail: null; error: null }
  | { status: "loaded"; detail: TherapistDetail; error: null }
  | { status: "error"; detail: null; error: string };

type TherapistCardProps = {
  therapist: TherapistSummary;
  active: boolean;
  onPress: (therapist: TherapistSummary) => void;
};

function TherapistCard({ therapist, active, onPress }: TherapistCardProps) {
  const theme = useTheme();

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: active ? theme.colors.primary : theme.colors.glassBorder,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
          backgroundColor: active
            ? "rgba(74,144,121,0.18)"
            : theme.colors.glassOverlay,
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
          backgroundColor: "rgba(74,144,121,0.15)",
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
        {therapist.recommended && <Text style={styles.badge}>推荐</Text>}
      </View>
      <Text style={styles.caption}>
        {therapist.specialties.join(" · ") || "未提供擅长领域"}
      </Text>
      <Text style={styles.caption}>
        {therapist.languages.join(" / ") || "未提供可用语言"}
      </Text>
      <Text style={styles.caption}>
        每次 {therapist.price} {therapist.currency}
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
            ? theme.colors.primary
            : theme.colors.borderSubtle,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.xs * 0.75,
          backgroundColor: active
            ? "rgba(74,144,121,0.15)"
            : "rgba(255,255,255,0.15)",
        },
        text: {
          color: active ? theme.colors.primary : theme.colors.textSecondary,
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
  const locale = Localization.locale ?? "zh-CN";
  const isZh = locale.startsWith("zh");
  const theme = useTheme();
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
  } = useTherapistDirectory(locale);

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
  const searchPlaceholder = isZh
    ? "搜索姓名、流派或关键词"
    : "Search by name, modality, or keyword";
  const recommendationTitle = isZh ? "AI 推荐顾问" : "AI recommendations";
  const recommendationSubtitle = isZh
    ? "根据你与 AI 的对话生成，供你优先考虑。"
    : "Rooted in your AI conversations so you can triage faster.";
  const recommendationLead = isZh
    ? "根据你与 AI 的对话，我们推荐以下三位顾问。"
    : "Based on your conversations with the AI, we recommend the following three therapists.";
  const recommendationSwatches = useMemo(
    () => [
      `${theme.colors.accentYellowGreen}66`,
      `${theme.colors.accentPinkGreen}66`,
      `${theme.colors.accentBlueGreen}66`,
    ],
    [
      theme.colors.accentYellowGreen,
      theme.colors.accentPinkGreen,
      theme.colors.accentBlueGreen,
    ],
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
          backgroundColor: "rgba(255,255,255,0.15)",
          padding: theme.spacing.sm,
        },
        recommendationItemPressed: {
          opacity: 0.9,
          transform: [{ scale: 0.99 }],
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
        listContent: {
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
        const detail = await loadTherapistDetail(therapist.id, locale);
        setDetailState({ status: "loaded", detail, error: null });
      } catch (err) {
        setDetailState({
          status: "error",
          detail: null,
          error:
            err instanceof Error
              ? err.message
              : "无法加载顾问详情，请稍后再试。",
        });
      }
    },
    [locale],
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
      />
    ),
    [handleSelect, selectedId],
  );

  return (
    <View style={styles.container}>
      <View>
        <Text style={styles.title}>顾问目录</Text>
        <Text style={styles.subtitle}>
          根据主题、语言和价格快速筛选合适的心理顾问。
        </Text>
      </View>

      <BlurView intensity={115} tint="light" style={styles.searchCard}>
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
          intensity={120}
          tint="light"
          style={styles.recommendationCard}
        >
          <Text style={styles.recommendationTitle}>{recommendationTitle}</Text>
          <Text style={styles.recommendationSubtitle}>
            {recommendationLead}
          </Text>
          <Text style={styles.recommendationMeta}>
            {recommendationSubtitle}
          </Text>
          <View style={styles.recommendationList}>
            {cachedRecommendations.map((recommendation, index) => {
              const label = String.fromCharCode(65 + index);
              const backgroundColor =
                recommendationSwatches[index % recommendationSwatches.length];
              const fallbackReason = isZh
                ? "与当前主题匹配。"
                : "Aligned with what you raised recently.";
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

      <BlurView intensity={115} tint="light" style={styles.filtersCard}>
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {source && (
            <Text style={styles.badge}>
              {source === "api" ? "实时数据" : "离线示例数据"}
            </Text>
          )}
          <Pressable onPress={handleResetFilters}>
            <Text style={styles.filterReset}>重置筛选</Text>
          </Pressable>
        </View>

        <View>
          <Text style={styles.filterLabel}>关注主题</Text>
          <View style={styles.chipRow}>
            {specialties.map((specialty) => (
              <FilterChip
                key={specialty}
                label={specialty}
                active={filters.specialty === specialty}
                onPress={() =>
                  setFilters((prev) => ({
                    ...prev,
                    specialty:
                      prev.specialty === specialty ? undefined : specialty,
                  }))
                }
              />
            ))}
            {specialties.length === 0 && (
              <Text style={styles.subtitle}>暂无主题信息</Text>
            )}
          </View>
        </View>

        <View>
          <Text style={styles.filterLabel}>支持语言</Text>
          <View style={styles.chipRow}>
            {languages.map((language) => (
              <FilterChip
                key={language}
                label={language}
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
              <Text style={styles.subtitle}>暂无语言信息</Text>
            )}
          </View>
        </View>

        <View>
          <Text style={styles.filterLabel}>价格下限（每次）</Text>
          <TextInput
            inputMode="numeric"
            keyboardType="number-pad"
            style={styles.input}
            placeholder={
              minPrice
                ? `最低 ${minPrice} ${therapists[0]?.currency ?? "CNY"}`
                : "不限"
            }
            placeholderTextColor={theme.colors.textSecondary}
            value={
              filters.minPrice === undefined ? "" : String(filters.minPrice)
            }
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
          <Text style={styles.filterLabel}>价格上限（每次）</Text>
          <TextInput
            inputMode="numeric"
            keyboardType="number-pad"
            style={styles.input}
            placeholder={
              maxPrice
                ? `最高 ${maxPrice} ${therapists[0]?.currency ?? "CNY"}`
                : "不限"
            }
            placeholderTextColor={theme.colors.textSecondary}
            value={
              filters.maxPrice === undefined ? "" : String(filters.maxPrice)
            }
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
          <Text style={styles.filterLabel}>只看推荐顾问</Text>
          <Switch
            value={Boolean(filters.recommendedOnly)}
            onValueChange={(value) =>
              setFilters((prev) => ({
                ...prev,
                recommendedOnly: value,
              }))
            }
            trackColor={{ true: "rgba(59,130,246,0.45)", false: "#ccc" }}
            thumbColor={
              filters.recommendedOnly ? theme.colors.primary : "#f4f3f4"
            }
          />
        </View>
      </BlurView>

      {isLoading ? (
        <View style={{ flex: 1, justifyContent: "center" }}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      ) : (
        <FlatList
          ref={flatListRef}
          data={filtered}
          keyExtractor={(item) => item.id}
          renderItem={renderTherapist}
          contentContainerStyle={styles.listContent}
          refreshing={isRefreshing}
          onRefresh={reload}
          ListEmptyComponent={
            <Text style={styles.emptyState}>
              没有符合条件的顾问，请调整筛选条件。
            </Text>
          }
        />
      )}

      <BlurView intensity={120} tint="light" style={styles.detailCard}>
        {detailState.status === "idle" && (
          <Text style={styles.subtitle}>选择顾问即可查看详细介绍。</Text>
        )}

        {detailState.status === "loading" && (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <ActivityIndicator size="small" color={theme.colors.primary} />
            <Text style={styles.subtitle}>正在载入顾问详情…</Text>
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
              {detailState.detail.biography || "暂无详细介绍。"}
            </Text>
            {detailState.detail.recommendationReason && (
              <Text
                style={[
                  styles.detailBody,
                  { color: theme.colors.primary, fontWeight: "600" },
                ]}
              >
                推荐理由：{detailState.detail.recommendationReason}
              </Text>
            )}
            <View style={{ gap: 4 }}>
              <Text style={styles.filterLabel}>可预约时间</Text>
              <View style={styles.availabilityRow}>
                {detailState.detail.availability.length === 0 ? (
                  <Text style={styles.subtitle}>暂无排期信息。</Text>
                ) : (
                  detailState.detail.availability.map((slot) => (
                    <Text key={slot} style={styles.availabilityBadge}>
                      {renderAvailabilitySlot(slot, locale)}
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
    </View>
  );
}
