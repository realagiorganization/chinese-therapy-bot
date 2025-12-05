import { useAuth } from "@context/AuthContext";
import { useLocale } from "@context/LocaleContext";
import { useTheme } from "@theme/ThemeProvider";
import { BlurView } from "expo-blur";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { translateBatch } from "@services/translation";

type CopyKey =
  | "title"
  | "subtitle"
  | "google_section"
  | "google_hint"
  | "google_placeholder"
  | "google_cta"
  | "demo_section"
  | "demo_hint"
  | "demo_label"
  | "demo_placeholder"
  | "demo_cta"
  | "locale_label"
  | "error_demo_required"
  | "error_google_required"
  | "loading_translations";

const BASE_LOCALE = "en-US";
const SUPPORTED_LOCALES = [
  { code: "zh-CN", label: "简体中文" },
  { code: "en-US", label: "English" },
  { code: "zh-TW", label: "繁體中文" },
  { code: "ru-RU", label: "Русский" },
] as const;
const BASE_COPY: Record<CopyKey, string> = {
  title: "Sign in to MindWell",
  subtitle: "Use your Google account or a demo code to continue.",
  google_section: "Google account",
  google_hint: "Complete the Google OAuth step, then paste the authorization code here.",
  google_placeholder: "Authorization code",
  google_cta: "Continue with Google",
  demo_section: "Demo access",
  demo_hint: "Enter the case-sensitive demo code provided by MindWell.",
  demo_label: "Demo code",
  demo_placeholder: "DEMO-TEAM",
  demo_cta: "Use demo code",
  locale_label: "Interface language",
  error_demo_required: "Enter the demo code.",
  error_google_required: "Enter the Google authorization code.",
  loading_translations: "Loading translations...",
};

const BASE_ENTRIES = Object.entries(BASE_COPY).map(([key, text]) => ({
  key,
  text,
}));

function normalizeLocale(code: string | null | undefined): string {
  if (!code) {
    return BASE_LOCALE;
  }
  const match = SUPPORTED_LOCALES.find(
    (option) => option.code.toLowerCase() === code.toLowerCase(),
  );
  return match?.code ?? BASE_LOCALE;
}

function mergeCopy(translations: Record<string, string>): Record<CopyKey, string> {
  const result: Record<CopyKey, string> = { ...BASE_COPY };
  (Object.keys(BASE_COPY) as CopyKey[]).forEach((key) => {
    if (translations[key]) {
      result[key] = translations[key] as string;
    }
  });
  return result;
}

function PrimaryButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const theme = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        button: {
          backgroundColor: theme.colors.primary,
          paddingVertical: theme.spacing.md,
          borderRadius: theme.radius.md,
          alignItems: "center",
          opacity: disabled ? 0.6 : 1,
        },
        label: {
          color: "#fff",
          fontWeight: "700",
          letterSpacing: 0.4,
          fontSize: 16,
        },
      }),
    [disabled, theme],
  );
  return (
    <Pressable onPress={onPress} disabled={disabled} style={styles.button}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

function SecondaryButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const theme = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        button: {
          borderWidth: 1,
          borderColor: theme.colors.textPrimary,
          paddingVertical: theme.spacing.md,
          borderRadius: theme.radius.md,
          alignItems: "center",
          opacity: disabled ? 0.6 : 1,
        },
        label: {
          color: theme.colors.textPrimary,
          fontWeight: "700",
          letterSpacing: 0.4,
          fontSize: 16,
        },
      }),
    [disabled, theme],
  );
  return (
    <Pressable onPress={onPress} disabled={disabled} style={styles.button}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

export function LoginScreen() {
  const { locale, setLocale } = useLocale();
  const { loginWithDemoCode, loginWithGoogle, isAuthenticating, error } = useAuth();
  const theme = useTheme();

  const [selectedLocale, setSelectedLocale] = useState<string>(
    locale ? normalizeLocale(locale) : BASE_LOCALE,
  );
  const [copy, setCopy] = useState<Record<CopyKey, string>>(BASE_COPY);
  const [demoCode, setDemoCode] = useState("");
  const [googleCode, setGoogleCode] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [isLoadingLocale, setLoadingLocale] = useState(false);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: "transparent",
          paddingHorizontal: theme.spacing.lg,
        },
        scrollContent: {
          flexGrow: 1,
          justifyContent: "center",
          paddingVertical: theme.spacing.xl,
        },
        card: {
          backgroundColor: theme.colors.glassOverlay,
          padding: theme.spacing.lg,
          borderRadius: theme.radius.lg,
          gap: theme.spacing.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
        },
        header: {
          gap: theme.spacing.xs,
        },
        heading: {
          fontSize: 24,
          fontWeight: "700",
          color: theme.colors.textPrimary,
        },
        subtitle: {
          fontSize: 14,
          color: theme.colors.textSecondary,
          lineHeight: 20,
        },
        localeLabel: {
          fontSize: 12,
          color: theme.colors.textSecondary,
        },
        localeBlock: {
          gap: theme.spacing.xs,
        },
        localeRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.xs,
        },
        localeScroll: {
          flexGrow: 0,
        },
        localeChip: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.pill,
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs * 0.8,
          backgroundColor: "transparent",
        },
        localeChipActive: {
          borderColor: theme.colors.textPrimary,
          backgroundColor: "rgba(255,255,255,0.4)",
        },
        localeChipLabel: {
          fontSize: 12,
          letterSpacing: 0.2,
          color: theme.colors.textSecondary,
        },
        localeChipLabelActive: {
          color: theme.colors.textPrimary,
          fontWeight: "700",
        },
        section: {
          gap: theme.spacing.sm,
        },
        sectionLabel: {
          fontSize: 12,
          letterSpacing: 0.4,
          color: theme.colors.textSecondary,
        },
        hint: {
          fontSize: 13,
          color: theme.colors.textSecondary,
          lineHeight: 18,
        },
        input: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.md,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          fontSize: 16,
          color: theme.colors.textPrimary,
        },
        divider: {
          height: 1,
          backgroundColor: theme.colors.surfaceMuted,
        },
        error: {
          color: theme.colors.danger,
          fontSize: 13,
        },
        loadingRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.xs,
        },
      }),
    [theme],
  );

  const t = useCallback(
    (key: CopyKey) => copy[key] ?? BASE_COPY[key],
    [copy],
  );

  const loadLocale = useCallback(
    async (nextLocale: string) => {
      const normalized = normalizeLocale(nextLocale);
      setSelectedLocale(normalized);
      if (normalized === BASE_LOCALE) {
        setCopy(BASE_COPY);
        await setLocale(normalized);
        return;
      }
      setLoadingLocale(true);
      try {
        const response = await translateBatch({
          targetLocale: normalized,
          sourceLocale: BASE_LOCALE,
          namespace: "mobile.login",
          entries: BASE_ENTRIES,
        });
        setCopy(mergeCopy(response.translations));
        await setLocale(normalized);
      } catch (err) {
        console.warn("Failed to load translations", err);
        setCopy(BASE_COPY);
      } finally {
        setLoadingLocale(false);
      }
    },
    [setLocale],
  );

  useEffect(() => {
    loadLocale(locale ?? BASE_LOCALE).catch(() => undefined);
  }, [locale, loadLocale]);

  const handleDemoSubmit = useCallback(async () => {
    const trimmed = demoCode.trim();
    if (!trimmed) {
      setLocalError(t("error_demo_required"));
      return;
    }
    setLocalError(null);
    await loginWithDemoCode(trimmed);
  }, [demoCode, loginWithDemoCode, t]);

  const handleGoogleSubmit = useCallback(async () => {
    const trimmed = googleCode.trim();
    if (!trimmed) {
      setLocalError(t("error_google_required"));
      return;
    }
    setLocalError(null);
    await loginWithGoogle(trimmed);
  }, [googleCode, loginWithGoogle, t]);

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <BlurView intensity={125} tint="light" style={styles.card}>
          <View style={styles.header}>
            <Text style={styles.heading}>MindWell</Text>
            <Text style={styles.subtitle}>{t("title")}</Text>
            <Text style={styles.hint}>{t("subtitle")}</Text>
            <View style={styles.localeBlock}>
              <Text style={styles.localeLabel}>{t("locale_label")}</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.localeRow}
                style={styles.localeScroll}
              >
                {SUPPORTED_LOCALES.map((locale) => (
                  <Pressable
                    key={locale.code}
                    onPress={() => loadLocale(locale.code)}
                    style={[
                      styles.localeChip,
                      selectedLocale === locale.code && styles.localeChipActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.localeChipLabel,
                        selectedLocale === locale.code &&
                          styles.localeChipLabelActive,
                      ]}
                    >
                      {locale.label}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>
              {isLoadingLocale && (
                <View style={styles.loadingRow}>
                  <ActivityIndicator
                    size="small"
                    color={theme.colors.textSecondary}
                  />
                  <Text style={styles.hint}>{t("loading_translations")}</Text>
                </View>
              )}
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionLabel}>{t("google_section")}</Text>
            <Text style={styles.hint}>{t("google_hint")}</Text>
            <TextInput
              value={googleCode}
              onChangeText={(text) => {
                setGoogleCode(text);
                setLocalError(null);
              }}
              style={styles.input}
              placeholder={t("google_placeholder")}
              autoCapitalize="none"
            />
            <PrimaryButton
              label={
                isAuthenticating ? `${t("google_cta")}...` : t("google_cta")
              }
              onPress={handleGoogleSubmit}
              disabled={isAuthenticating || googleCode.trim().length === 0}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.section}>
            <Text style={styles.sectionLabel}>{t("demo_section")}</Text>
            <Text style={styles.hint}>{t("demo_hint")}</Text>
            <TextInput
              value={demoCode}
              onChangeText={(text) => {
                setDemoCode(text);
                setLocalError(null);
              }}
              style={styles.input}
              placeholder={t("demo_placeholder")}
              autoCapitalize="characters"
            />
            <SecondaryButton
              label={
                isAuthenticating ? `${t("demo_cta")}...` : t("demo_cta")
              }
              onPress={handleDemoSubmit}
              disabled={isAuthenticating || demoCode.trim().length === 0}
            />
          </View>

          {(localError || error) && (
            <Text style={styles.error}>{localError ?? error}</Text>
          )}
        </BlurView>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
