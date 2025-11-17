import { ConnectivityBanner } from "@components/ConnectivityBanner";
import { AuthProvider, useAuth } from "@context/AuthContext";
import { VoiceSettingsProvider } from "@context/VoiceSettingsContext";
import { usePushNotifications } from "@hooks/usePushNotifications";
import { useStartupProfiler } from "@hooks/useStartupProfiler";
import { ChatScreen } from "@screens/ChatScreen";
import { JourneyScreen } from "@screens/JourneyScreen";
import { LoginScreen } from "@screens/LoginScreen";
import { SettingsScreen } from "@screens/SettingsScreen";
import { TherapistDirectoryScreen } from "@screens/TherapistDirectoryScreen";
import { ThemeProvider, useTheme } from "@theme/ThemeProvider";
import { BlurView } from "expo-blur";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  Platform,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { lightThemeTokens } from "shared/design-tokens";

const serifFontStack = lightThemeTokens.typography.fontFamilyBase
  .split(",")
  .map((token) => token.replace(/"/g, "").trim())
  .filter(Boolean);

const serifFontFamily =
  Platform.select({
    ios:
      serifFontStack.find(
        (font) => font.toLowerCase() === "times new roman",
      ) ?? serifFontStack[0] ?? "Times New Roman",
    android:
      serifFontStack.find((font) => font.toLowerCase() === "serif") ??
      "serif",
    default: serifFontStack[0] ?? "Georgia",
  }) ?? "Georgia";

type TextWithDefaults = typeof Text & { defaultProps?: Text["props"] };
type TextInputWithDefaults = typeof TextInput & {
  defaultProps?: TextInput["props"];
};

function ensureSerifTypography() {
  if (!serifFontFamily) {
    return;
  }

  const TextComponent = Text as TextWithDefaults;
  TextComponent.defaultProps = {
    ...(TextComponent.defaultProps ?? {}),
    style: StyleSheet.flatten([
      TextComponent.defaultProps?.style,
      { fontFamily: serifFontFamily },
    ]),
  };

  const InputComponent = TextInput as TextInputWithDefaults;
  InputComponent.defaultProps = {
    ...(InputComponent.defaultProps ?? {}),
    style: StyleSheet.flatten([
      InputComponent.defaultProps?.style,
      { fontFamily: serifFontFamily },
    ]),
  };
}

ensureSerifTypography();

type MobileTab = "chat" | "journey" | "therapists" | "settings";

function AuthenticatedShell() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const [activeTab, setActiveTab] = useState<MobileTab>("chat");
  const [lastNonChatTab, setLastNonChatTab] = useState<MobileTab>("journey");
  const [keyboardVisible, setKeyboardVisible] = useState(false);

  useEffect(() => {
    const show = Keyboard.addListener("keyboardDidShow", () =>
      setKeyboardVisible(true),
    );
    const hide = Keyboard.addListener("keyboardDidHide", () =>
      setKeyboardVisible(false),
    );
    return () => {
      show.remove();
      hide.remove();
    };
  }, []);

  const androidRipple = useMemo(
    () =>
      Platform.OS === "android"
        ? { color: "rgba(255,255,255,0.2)", foreground: true }
        : undefined,
    [],
  );

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          paddingHorizontal: theme.spacing.lg,
          paddingBottom: keyboardVisible
            ? theme.spacing.sm
            : Math.max(insets.bottom, theme.spacing.lg),
        },
        content: {
          flex: 1,
          paddingTop: theme.spacing.lg,
        },
        tabWrapper: {
          marginTop: theme.spacing.md,
        },
        tabBar: {
          borderRadius: theme.radius.lg,
          borderWidth: 1,
          borderColor: theme.colors.glassBorder,
          overflow: "hidden",
        },
        tabButton: {
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          paddingVertical: theme.spacing.sm,
          borderRightWidth: StyleSheet.hairlineWidth,
          borderColor: "rgba(255,255,255,0.4)",
          backgroundColor: "transparent",
        },
        tabButtonLast: {
          borderRightWidth: 0,
        },
        tabLabel: {
          fontSize: 12,
          letterSpacing: 0.6,
          color: theme.colors.textSecondary,
        },
        tabLabelActive: {
          color: theme.colors.textPrimary,
          fontWeight: "600",
        },
        tabButtonActive: {
          borderColor: theme.colors.textPrimary,
        },
        tabDot: {
          width: 6,
          height: 6,
          borderRadius: 3,
          marginTop: 4,
        },
      }),
    [insets.bottom, keyboardVisible, theme],
  );

  const handleTabChange = useCallback((tab: MobileTab) => {
    setActiveTab((current) => {
      if (current === tab) {
        return current;
      }
      if (tab !== "chat") {
        setLastNonChatTab(tab);
      }
      if (Platform.OS === "ios" || Platform.OS === "android") {
        Haptics.selectionAsync().catch(() => undefined);
      }
      return tab;
    });
  }, []);

  const handleChatBack = useCallback(() => {
    setActiveTab(lastNonChatTab === "chat" ? "journey" : lastNonChatTab);
  }, [lastNonChatTab]);

  const tabItems = useMemo(
    () => [
      { key: "chat" as const, label: "对话" },
      { key: "journey" as const, label: "旅程" },
      { key: "therapists" as const, label: "顾问" },
      { key: "settings" as const, label: "设置" },
    ],
    [],
  );

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {activeTab === "chat" && <ChatScreen onNavigateBack={handleChatBack} />}
        {activeTab === "journey" && <JourneyScreen />}
        {activeTab === "therapists" && <TherapistDirectoryScreen />}
        {activeTab === "settings" && <SettingsScreen />}
      </View>
      {!keyboardVisible && (
        <View style={styles.tabWrapper}>
      <BlurView intensity={140} tint="light" style={styles.tabBar}>
            {tabItems.map((tab, index) => {
              const isActive = activeTab === tab.key;
              return (
                <Pressable
                  key={tab.key}
                  android_ripple={androidRipple}
                  onPress={() => handleTabChange(tab.key)}
                  style={[
                    styles.tabButton,
                    index === tabItems.length - 1 && styles.tabButtonLast,
                    isActive && styles.tabButtonActive,
                  ]}
                >
                  <Text
                    style={[styles.tabLabel, isActive && styles.tabLabelActive]}
                  >
                    {tab.label}
                  </Text>
                  <View
                    style={[
                      styles.tabDot,
                      {
                        backgroundColor: isActive
                          ? theme.colors.primary
                          : "transparent",
                        borderWidth: isActive ? 0 : StyleSheet.hairlineWidth,
                        borderColor: theme.colors.borderSubtle,
                      },
                    ]}
                  />
                </Pressable>
              );
            })}
          </BlurView>
        </View>
      )}
    </View>
  );
}

function AppShell() {
  const { status, userId } = useAuth();
  const theme = useTheme();
  const markStartup = useStartupProfiler({ label: "shell" });
  usePushNotifications(status === "authenticated" ? userId : null);

  useEffect(() => {
    if (status === "loading") {
      return;
    }
    markStartup(`auth-${status}`);
  }, [markStartup, status]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        gradient: {
          flex: 1,
        },
        container: {
          flex: 1,
          backgroundColor: "transparent",
          paddingTop: theme.spacing.md,
        },
        loadingState: {
          alignItems: "center",
          justifyContent: "center",
        },
      }),
    [theme.spacing.md],
  );

  const gradientColors = useMemo(
    () => [
      theme.colors.gradientBottom,
      theme.colors.gradientMid,
      theme.colors.gradientTop,
    ],
    [
      theme.colors.gradientTop,
      theme.colors.gradientMid,
      theme.colors.gradientBottom,
    ],
  );
  const gradientProps = useMemo(
    () => ({
      start: { x: 0.5, y: 1 },
      end: { x: 0.5, y: 0 },
      locations: [0, 0.35, 0.78],
    }),
    [],
  );

  if (status === "loading") {
    return (
      <LinearGradient
        {...gradientProps}
        colors={gradientColors}
        style={styles.gradient}
      >
        <SafeAreaView style={[styles.container, styles.loadingState]}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </SafeAreaView>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient
      {...gradientProps}
      colors={gradientColors}
      style={styles.gradient}
    >
      <SafeAreaView style={styles.container}>
        <ConnectivityBanner placement="top" />
        {status === "authenticated" ? <AuthenticatedShell /> : <LoginScreen />}
      </SafeAreaView>
    </LinearGradient>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <VoiceSettingsProvider>
            <AuthProvider>
              <ExpoStatusBar style="dark" />
              <AppShell />
            </AuthProvider>
          </VoiceSettingsProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
