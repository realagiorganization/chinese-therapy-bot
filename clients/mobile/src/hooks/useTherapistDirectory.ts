import { useCallback, useEffect, useMemo, useState } from "react";

import {
  applyFilters,
  loadTherapists,
  type TherapistListSource,
} from "../services/therapists";
import type { TherapistFilters, TherapistSummary } from "../types/therapists";

export type TherapistDirectoryState = {
  therapists: TherapistSummary[];
  filtered: TherapistSummary[];
  filters: TherapistFilters;
  source: TherapistListSource | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: Error | null;
  specialties: string[];
  languages: string[];
  maxPrice: number | null;
  setFilters: (updater: (prev: TherapistFilters) => TherapistFilters) => void;
  resetFilters: () => void;
  reload: () => Promise<void>;
};

const INITIAL_FILTERS: TherapistFilters = {
  specialty: undefined,
  language: undefined,
  recommendedOnly: false,
  maxPrice: undefined,
};

export function useTherapistDirectory(
  locale = "zh-CN",
): TherapistDirectoryState {
  const [therapists, setTherapists] = useState<TherapistSummary[]>([]);
  const [filters, setFiltersState] =
    useState<TherapistFilters>(INITIAL_FILTERS);
  const [source, setSource] = useState<TherapistListSource | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDirectory = useCallback(async () => {
    const result = await loadTherapists(locale);
    setTherapists(result.therapists);
    setSource(result.source);
  }, [locale]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setIsLoading(true);
      try {
        await fetchDirectory();
        if (!cancelled) {
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Therapist load error"),
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [fetchDirectory]);

  const reload = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await fetchDirectory();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Therapist load error"));
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchDirectory]);

  const filtered = useMemo(
    () => applyFilters(therapists, filters),
    [therapists, filters],
  );

  const specialties = useMemo(() => {
    const pool = new Set<string>();
    therapists.forEach((therapist) => {
      therapist.specialties.forEach((item) => pool.add(item));
    });
    return Array.from(pool).sort((a, b) => a.localeCompare(b, locale));
  }, [therapists, locale]);

  const languages = useMemo(() => {
    const pool = new Set<string>();
    therapists.forEach((therapist) => {
      therapist.languages.forEach((item) => pool.add(item));
    });
    return Array.from(pool).sort((a, b) => a.localeCompare(b, locale));
  }, [therapists, locale]);

  const maxPrice = useMemo(() => {
    if (therapists.length === 0) {
      return null;
    }
    return Math.max(...therapists.map((therapist) => therapist.price));
  }, [therapists]);

  const setFilters = useCallback(
    (updater: (prev: TherapistFilters) => TherapistFilters) => {
      setFiltersState((prev) => updater({ ...prev }));
    },
    [],
  );

  const resetFilters = useCallback(() => {
    setFiltersState(INITIAL_FILTERS);
  }, []);

  return {
    therapists,
    filtered,
    filters,
    source,
    isLoading,
    isRefreshing,
    error,
    specialties,
    languages,
    maxPrice,
    setFilters,
    resetFilters,
    reload,
  };
}
