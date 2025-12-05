import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const LOCALE_STORAGE_KEY = "@mindwell/mobile/locale";
const DEFAULT_LOCALE = "zh-CN";

type LocaleContextValue = {
  locale: string;
  setLocale: (next: string) => Promise<void>;
  loading: boolean;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<string>(DEFAULT_LOCALE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const bootstrap = async () => {
      try {
        const stored = await AsyncStorage.getItem(LOCALE_STORAGE_KEY);
        if (stored && mounted) {
          setLocaleState(stored);
        }
      } catch (err) {
        console.warn("Failed to restore locale", err);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    bootstrap().catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  const setLocale = useCallback(async (next: string) => {
    const normalized = next?.trim() || DEFAULT_LOCALE;
    setLocaleState(normalized);
    try {
      await AsyncStorage.setItem(LOCALE_STORAGE_KEY, normalized);
    } catch (err) {
      console.warn("Failed to persist locale", err);
    }
  }, []);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      loading,
    }),
    [locale, setLocale, loading],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return ctx;
}

export const LOCALE_KEYS = {
  storage: LOCALE_STORAGE_KEY,
  default: DEFAULT_LOCALE,
} as const;
