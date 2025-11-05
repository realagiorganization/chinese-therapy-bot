import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { loadTherapistDetail } from "../api/therapists";
import type { TherapistDetail, TherapistSummary } from "../api/types";
import { Button, Card, Typography } from "../design-system";
import { useTherapistDirectory } from "../hooks/useTherapistDirectory";
import { formatTherapistDisplayName } from "../utils/therapistDisplayName";

type DetailState =
  | { status: "idle"; detail: null; error: null }
  | { status: "loading"; detail: null; error: null }
  | { status: "loaded"; detail: TherapistDetail; error: null }
  | { status: "error"; detail: null; error: string };

function formatCurrency(value: number, currency: string, locale: string) {
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      currencyDisplay: "symbol",
      maximumFractionDigits: 0
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

function formatAvailability(slot: string, locale: string) {
  const parsed = new Date(slot);
  if (!Number.isNaN(parsed.getTime())) {
    return new Intl.DateTimeFormat(locale, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }).format(parsed);
  }
  return slot;
}

export function TherapistDirectory() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language ?? "zh-CN";

  const {
    filtered,
    filters,
    setFilters,
    resetFilters,
    specialties,
    languages,
    minPrice,
    isLoading,
    source,
    maxPrice
  } = useTherapistDirectory(locale);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailState, setDetailState] = useState<DetailState>({
    status: "idle",
    detail: null,
    error: null
  });

  const handleSelect = useCallback(
    async (therapist: TherapistSummary) => {
      setSelectedId(therapist.id);
      setDetailState({ status: "loading", detail: null, error: null });
      try {
        const detail = await loadTherapistDetail(therapist.id, locale);
        setDetailState({ status: "loaded", detail, error: null });
      } catch (error) {
        setDetailState({
          status: "error",
          detail: null,
          error: error instanceof Error ? error.message : String(error)
        });
      }
    },
    [locale]
  );

  const handleCloseDetail = useCallback(() => {
    setSelectedId(null);
    setDetailState({ status: "idle", detail: null, error: null });
  }, []);

  const selectedDetail = detailState.status === "loaded" ? detailState.detail : null;

  const languagesById = useMemo(
    () =>
      filtered.reduce<Record<string, string>>((accumulator, therapist) => {
        accumulator[therapist.id] = therapist.languages.join(" / ");
        return accumulator;
      }, {}),
    [filtered]
  );

  return (
    <section style={{ display: "grid", gap: "var(--mw-spacing-md)" }}>
      <Card padding="lg" elevated style={{ display: "grid", gap: "var(--mw-spacing-md)" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "var(--mw-spacing-sm)",
            flexWrap: "wrap",
            alignItems: "flex-start"
          }}
        >
          <div style={{ display: "grid", gap: "4px" }}>
            <Typography variant="subtitle">{t("therapists.directory_title")}</Typography>
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {t("therapists.directory_subtitle")}
            </Typography>
          </div>
          {source && (
            <Typography
              variant="caption"
              style={{
                background: "rgba(59,130,246,0.12)",
                color: "var(--mw-color-primary)",
                borderRadius: "var(--mw-radius-pill)",
                padding: "4px 10px",
                fontWeight: 500
              }}
            >
              {t(
                source === "api"
                  ? "therapists.filters.source_api"
                  : "therapists.filters.source_fallback"
              )}
            </Typography>
          )}
        </div>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--mw-spacing-md)"
          }}
        >
          <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
            <span style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.specialty")}
            </span>
            <select
              value={filters.specialty ?? ""}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  specialty: event.target.value || undefined
                }))
              }
              style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--mw-border-subtle)" }}
            >
              <option value="">{t("therapists.filters.any")}</option>
              {specialties.map((specialty) => (
                <option key={specialty} value={specialty}>
                  {specialty}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
            <span style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.language")}
            </span>
            <select
              value={filters.language ?? ""}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  language: event.target.value || undefined
                }))
              }
              style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--mw-border-subtle)" }}
            >
              <option value="">{t("therapists.filters.any")}</option>
              {languages.map((language) => (
                <option key={language} value={language}>
                  {language}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
            <span style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.min_price", { currency: "CNY" })}
            </span>
            <input
              type="number"
              min={0}
              max={maxPrice ?? undefined}
              value={filters.minPrice ?? ""}
              onChange={(event) => {
                const nextValue = event.target.value;
                setFilters((prev) => {
                  if (nextValue === "") {
                    return { ...prev, minPrice: undefined };
                  }
                  const numeric = Number.parseInt(nextValue, 10);
                  return {
                    ...prev,
                    minPrice: Number.isNaN(numeric) ? prev.minPrice : numeric
                  };
                });
              }}
              placeholder={
                minPrice !== null
                  ? t("therapists.filters.price_placeholder_min", {
                      value: minPrice
                    })
                  : undefined
              }
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "1px solid var(--mw-border-subtle)",
                width: "140px"
              }}
            />
          </label>

          <label style={{ display: "grid", gap: "4px", fontSize: "0.85rem" }}>
            <span style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.max_price", { currency: "CNY" })}
            </span>
            <input
              type="number"
              min={0}
              max={maxPrice ?? undefined}
              value={filters.maxPrice ?? ""}
              onChange={(event) => {
                const nextValue = event.target.value;
                setFilters((prev) => {
                  if (nextValue === "") {
                    return { ...prev, maxPrice: undefined };
                  }
                  const numeric = Number.parseInt(nextValue, 10);
                  return {
                    ...prev,
                    maxPrice: Number.isNaN(numeric) ? prev.maxPrice : numeric
                  };
                });
              }}
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "1px solid var(--mw-border-subtle)",
                width: "140px"
              }}
            />
          </label>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.85rem",
              color: "var(--text-secondary)"
            }}
          >
            <input
              type="checkbox"
              checked={Boolean(filters.recommendedOnly)}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  recommendedOnly: event.target.checked
                }))
              }
            />
            {t("therapists.filters.recommended_only")}
          </label>

          <Button type="button" variant="ghost" onClick={resetFilters}>
            {t("therapists.filters.reset")}
          </Button>
        </div>

        {isLoading && (
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {t("therapists.filters.loading")}
          </Typography>
        )}
      </Card>

      <div
        style={{
          display: "grid",
          gap: "var(--mw-spacing-md)",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))"
        }}
      >
        {!isLoading && filtered.length === 0 ? (
          <Card padding="md">
            <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
              {t("therapists.filters.empty_state")}
            </Typography>
          </Card>
        ) : (
          filtered.map((therapist) => {
            const isActive = therapist.id === selectedId;
            return (
              <Card
                key={therapist.id}
                padding="md"
                elevated={isActive}
                style={{
                  display: "grid",
                  gap: "var(--mw-spacing-xs)",
                  border: isActive ? "1px solid var(--mw-color-primary)" : "1px solid var(--mw-border-subtle)"
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: "var(--mw-spacing-xs)"
                  }}
                >
                  <div style={{ display: "grid", gap: "2px" }}>
                    <Typography variant="body" style={{ fontWeight: 600 }}>
                      {formatTherapistDisplayName(therapist.id, therapist.name, t)}
                    </Typography>
                    <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                      {therapist.title}
                    </Typography>
                  </div>
                  {therapist.recommended && (
                    <span
                      style={{
                        background: "rgba(59,130,246,0.12)",
                        color: "var(--mw-color-primary)",
                        borderRadius: "var(--mw-radius-pill)",
                        padding: "2px 8px",
                        fontSize: "0.75rem",
                        fontWeight: 600
                      }}
                    >
                      {t("therapists.badge_recommended")}
                    </span>
                  )}
                </div>

                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {therapist.specialties.join(" · ")}
                </Typography>

                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.languages", {
                    languages: languagesById[therapist.id] ?? therapist.languages.join(" / ")
                  })}
                </Typography>

                <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.price", {
                    price: formatCurrency(therapist.price, therapist.currency ?? "CNY", locale)
                  })}
                </Typography>

                <Button type="button" variant="ghost" onClick={() => handleSelect(therapist)}>
                  {t("therapists.view_profile")}
                </Button>
              </Card>
            );
          })
        )}
      </div>

      <Card padding="lg" style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "var(--mw-spacing-sm)"
          }}
        >
          <Typography variant="subtitle">{t("therapists.detail_panel_title")}</Typography>
          {selectedId && (
            <Button type="button" variant="ghost" size="sm" onClick={handleCloseDetail}>
              {t("therapists.detail_close")}
            </Button>
          )}
        </div>

        {detailState.status === "idle" && (
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {t("therapists.detail_placeholder")}
          </Typography>
        )}

        {detailState.status === "loading" && (
          <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
            {t("therapists.detail_loading")}
          </Typography>
        )}

        {detailState.status === "error" && (
          <Typography variant="body" style={{ color: "var(--mw-color-danger)" }}>
            {t("therapists.detail_error")} ({detailState.error})
          </Typography>
        )}

        {selectedDetail && (
          <div style={{ display: "grid", gap: "var(--mw-spacing-sm)" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--mw-spacing-xs)" }}>
              <Typography variant="title">
                {formatTherapistDisplayName(selectedDetail.id, selectedDetail.name, t)}
              </Typography>
              {selectedDetail.recommended && (
                <span
                  style={{
                    background: "rgba(59,130,246,0.12)",
                    color: "var(--mw-color-primary)",
                    borderRadius: "var(--mw-radius-pill)",
                    padding: "3px 10px",
                    fontSize: "0.75rem",
                    fontWeight: 600
                  }}
                >
                  {t("therapists.badge_recommended")}
                </span>
              )}
            </div>
            <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
              {selectedDetail.title}
            </Typography>
            <Typography variant="body">{selectedDetail.biography || t("therapists.detail_no_bio")}</Typography>
            {selectedDetail.recommendationReason && (
              <Typography variant="caption" style={{ color: "var(--mw-color-primary)" }}>
                {t("therapists.recommendation_reason", {
                  reason: selectedDetail.recommendationReason
                })}
              </Typography>
            )}
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {t("therapists.languages", {
                languages: selectedDetail.languages.join(" / ")
              })}
            </Typography>
            <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
              {t("therapists.price", {
                price: formatCurrency(selectedDetail.price, selectedDetail.currency ?? "CNY", locale)
              })}
            </Typography>
            <div style={{ display: "grid", gap: "var(--mw-spacing-xs)" }}>
              <Typography variant="caption" style={{ color: "var(--text-secondary)" }}>
                {t("therapists.availability_label")}
              </Typography>
              {selectedDetail.availability.length === 0 ? (
                <Typography variant="body" style={{ color: "var(--text-secondary)" }}>
                  {t("therapists.no_availability")}
                </Typography>
              ) : (
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: "20px",
                    color: "var(--text-secondary)",
                    fontSize: "0.9rem"
                  }}
                >
                  {selectedDetail.availability.map((slot) => (
                    <li key={slot}>{formatAvailability(slot, locale)}</li>
                  ))}
                </ul>
              )}
            </div>
            <div style={{ display: "flex", gap: "var(--mw-spacing-sm)" }}>
              <Button type="button">{t("therapists.book")}</Button>
              <Button type="button" variant="secondary">
                {t("therapists.share_profile")}
              </Button>
            </div>
          </div>
        )}
      </Card>
    </section>
  );
}
