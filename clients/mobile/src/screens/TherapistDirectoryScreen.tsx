import * as Localization from "expo-localization";
import { useCallback, useEffect, useMemo, useState } from "react";
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
import { loadTherapistDetail } from "../services/therapists";
import { useTheme } from "../theme/ThemeProvider";
import type { TherapistDetail, TherapistSummary } from "../types/therapists";

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
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: active
            ? theme.colors.primary
            : theme.colors.borderSubtle,
          padding: theme.spacing.md,
          gap: theme.spacing.xs,
          backgroundColor: active
            ? "rgba(59,130,246,0.08)"
            : theme.colors.surfaceCard,
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
          backgroundColor: "rgba(59,130,246,0.12)",
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
            ? "rgba(59,130,246,0.12)"
            : theme.colors.surfaceMuted,
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
  const theme = useTheme();
  const {
    therapists,
    filtered,
    filters,
    setFilters,
    resetFilters,
    specialties,
    languages,
    maxPrice,
    source,
    isLoading,
    isRefreshing,
    reload,
    error,
  } = useTherapistDirectory(locale);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailState, setDetailState] = useState<DetailState>({
    status: "idle",
    detail: null,
    error: null,
  });

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
          backgroundColor: theme.colors.surfaceBackground,
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
        badge: {
          backgroundColor: "rgba(59,130,246,0.12)",
          color: theme.colors.primary,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          fontSize: 12,
          fontWeight: "600",
        },
        filtersCard: {
          borderRadius: theme.radius.md,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing.md,
          gap: theme.spacing.md,
          backgroundColor: theme.colors.surfaceCard,
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
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing.lg,
          gap: theme.spacing.sm,
          backgroundColor: theme.colors.surfaceCard,
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

      <View style={styles.filtersCard}>
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
      </View>

      {isLoading ? (
        <View style={{ flex: 1, justifyContent: "center" }}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      ) : (
        <FlatList
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

      <View style={styles.detailCard}>
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
      </View>
    </View>
  );
}
