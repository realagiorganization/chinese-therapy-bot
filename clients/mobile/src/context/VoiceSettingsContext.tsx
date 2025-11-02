import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type VoiceSettings = {
  enabled: boolean;
  rate: number;
  pitch: number;
};

type VoiceSettingsContextValue = VoiceSettings & {
  loading: boolean;
  setEnabled: (value: boolean) => void;
  setRate: (value: number) => void;
  setPitch: (value: number) => void;
  reset: () => void;
};

const STORAGE_KEY = "mindwell.voiceSettings";
const DEFAULT_SETTINGS: VoiceSettings = {
  enabled: true,
  rate: 1,
  pitch: 1,
};

const VoiceSettingsContext = createContext<VoiceSettingsContextValue | null>(
  null,
);

function coerceScalar(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function sanitizeSettings(candidate: Partial<VoiceSettings>): VoiceSettings {
  const enabled =
    typeof candidate.enabled === "boolean"
      ? candidate.enabled
      : DEFAULT_SETTINGS.enabled;
  const rateRaw = coerceScalar(candidate.rate, DEFAULT_SETTINGS.rate);
  const pitchRaw = coerceScalar(candidate.pitch, DEFAULT_SETTINGS.pitch);

  const clamp = (input: number, min: number, max: number) =>
    Math.max(min, Math.min(max, input));

  return {
    enabled,
    rate: clamp(rateRaw, 0.5, 1.5),
    pitch: clamp(pitchRaw, 0.6, 1.4),
  };
}

export function VoiceSettingsProvider({ children }: PropsWithChildren) {
  const [settings, setSettings] = useState<VoiceSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState<boolean>(true);
  const hydratedRef = useRef<boolean>(false);
  const pendingWriteRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let isMounted = true;
    const hydrate = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (!stored || !isMounted) {
          return;
        }
        const parsed = JSON.parse(stored) as Partial<VoiceSettings>;
        const normalized = sanitizeSettings(parsed);
        setSettings(normalized);
      } catch {
        // Ignore storage errors and fall back to defaults.
      } finally {
        if (isMounted) {
          hydratedRef.current = true;
          setLoading(false);
        }
      }
    };

    hydrate().catch(() => {
      if (isMounted) {
        hydratedRef.current = true;
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
      if (pendingWriteRef.current) {
        clearTimeout(pendingWriteRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!hydratedRef.current) {
      return;
    }

    if (pendingWriteRef.current) {
      clearTimeout(pendingWriteRef.current);
    }

    pendingWriteRef.current = setTimeout(() => {
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(settings)).catch(() => {
        // Persisting preferences is best-effort; failures are non-fatal.
      });
      pendingWriteRef.current = null;
    }, 150);
  }, [settings]);

  const setEnabled = useCallback((value: boolean) => {
    hydratedRef.current = true;
    setSettings((prev) => {
      if (prev.enabled === value) {
        return prev;
      }
      return { ...prev, enabled: value };
    });
  }, []);

  const setRate = useCallback((value: number) => {
    hydratedRef.current = true;
    setSettings((prev) => {
      if (prev.rate === value) {
        return prev;
      }
      return { ...prev, rate: value };
    });
  }, []);

  const setPitch = useCallback((value: number) => {
    hydratedRef.current = true;
    setSettings((prev) => {
      if (prev.pitch === value) {
        return prev;
      }
      return { ...prev, pitch: value };
    });
  }, []);

  const reset = useCallback(() => {
    hydratedRef.current = true;
    setSettings(DEFAULT_SETTINGS);
  }, []);

  const value = useMemo<VoiceSettingsContextValue>(
    () => ({
      ...settings,
      loading,
      setEnabled,
      setRate,
      setPitch,
      reset,
    }),
    [settings, loading, setEnabled, setRate, setPitch, reset],
  );

  return (
    <VoiceSettingsContext.Provider value={value}>
      {children}
    </VoiceSettingsContext.Provider>
  );
}

export function useVoiceSettings(): VoiceSettingsContextValue {
  const context = useContext(VoiceSettingsContext);
  if (!context) {
    throw new Error(
      "useVoiceSettings must be used within a VoiceSettingsProvider",
    );
  }
  return context;
}
