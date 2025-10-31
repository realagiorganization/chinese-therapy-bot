import { useEffect, useMemo, useState } from "react";

import { loadTherapists } from "../api/therapists";
import type { TherapistFilters, TherapistSummary } from "../api/types";

export type TherapistDirectoryState = {
  therapists: TherapistSummary[];
  filtered: TherapistSummary[];
  filters: TherapistFilters;
  source: "api" | "fallback" | null;
  isLoading: boolean;
  error?: Error | null;
  specialties: string[];
  languages: string[];
  maxPrice: number | null;
  setFilters: (updater: (prev: TherapistFilters) => TherapistFilters) => void;
  resetFilters: () => void;
};

const INITIAL_FILTERS: TherapistFilters = {
  specialty: undefined,
  language: undefined,
  recommendedOnly: false,
  maxPrice: undefined
};

export function useTherapistDirectory(): TherapistDirectoryState {
  const [therapists, setTherapists] = useState<TherapistSummary[]>([]);
  const [filters, setFiltersState] = useState<TherapistFilters>(INITIAL_FILTERS);
  const [source, setSource] = useState<"api" | "fallback" | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        const result = await loadTherapists();
        if (!cancelled) {
          setTherapists(result.therapists);
          setSource(result.source);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error("Unknown therapist load error"));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const specialties = useMemo(() => {
    const pool = new Set<string>();
    therapists.forEach((therapist) => {
      therapist.specialties.forEach((item) => pool.add(item));
    });
    return Array.from(pool).sort();
  }, [therapists]);

  const languages = useMemo(() => {
    const pool = new Set<string>();
    therapists.forEach((therapist) => {
      therapist.languages.forEach((item) => pool.add(item));
    });
    return Array.from(pool).sort();
  }, [therapists]);

  const maxPrice = useMemo(() => {
    if (therapists.length === 0) {
      return null;
    }
    return Math.max(...therapists.map((therapist) => therapist.price));
  }, [therapists]);

  const filtered = useMemo(() => {
    return therapists.filter((therapist) => {
      if (filters.recommendedOnly && !therapist.recommended) {
        return false;
      }
      if (filters.specialty && !therapist.specialties.includes(filters.specialty)) {
        return false;
      }
      if (filters.language && !therapist.languages.includes(filters.language)) {
        return false;
      }
      if (filters.maxPrice && therapist.price > filters.maxPrice) {
        return false;
      }
      return true;
    });
  }, [therapists, filters]);

  const setFilters = (updater: (prev: TherapistFilters) => TherapistFilters) => {
    setFiltersState((prev) => updater({ ...prev }));
  };

  const resetFilters = () => {
    setFiltersState(INITIAL_FILTERS);
  };

  return {
    therapists,
    filtered,
    filters,
    source,
    isLoading,
    error,
    specialties,
    languages,
    maxPrice,
    setFilters,
    resetFilters
  };
}
