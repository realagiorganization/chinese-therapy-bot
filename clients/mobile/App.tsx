import { AuthProvider, useAuth } from "@context/AuthContext";
import { usePushNotifications } from "@hooks/usePushNotifications";
import { useStartupProfiler } from "@hooks/useStartupProfiler";
import { ChatScreen } from "@screens/ChatScreen";
import { JourneyScreen } from "@screens/JourneyScreen";
import { LoginScreen } from "@screens/LoginScreen";
import { TherapistDirectoryScreen } from "@screens/TherapistDirectoryScreen";
import { ThemeProvider, useTheme } from "@theme/ThemeProvider";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

type MobileTab = "chat" | "journey" | "therapists";

function AuthenticatedShell() {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState<MobileTab>("chat");

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
        },
        tabBar: {
          flexDirection: "row",
          borderBottomWidth: 1,
          borderColor: theme.colors.borderSubtle,
          backgroundColor: theme.colors.surfaceCard,
        },
        tabButton: {
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          paddingVertical: theme.spacing.md,
          position: "relative",
        },
        tabLabel: {
          fontSize: 14,
          color: theme.colors.textSecondary,
        },
        tabLabelActive: {
          color: theme.colors.primary,
          fontWeight: "600",
        },
        tabIndicator: {
          position: "absolute",
          bottom: 0,
          height: 2,
          width: "60%",
          borderRadius: theme.radius.pill,
          backgroundColor: theme.colors.primary,
        },
        tabButtonActive: {
          backgroundColor: "rgba(59,130,246,0.08)",
        },
        content: {
          flex: 1,
        },
      }),
    [theme],
  );

  return (
    <View style={styles.container}>
      <View style={styles.tabBar}>
        <Pressable
          onPress={() => setActiveTab("chat")}
          style={[
            styles.tabButton,
            activeTab === "chat" && styles.tabButtonActive,
          ]}
        >
          <Text
            style={[
              styles.tabLabel,
              activeTab === "chat" && styles.tabLabelActive,
            ]}
          >
            对话
          </Text>
          {activeTab === "chat" && <View style={styles.tabIndicator} />}
        </Pressable>
        <Pressable
          onPress={() => setActiveTab("journey")}
          style={[
            styles.tabButton,
            activeTab === "journey" && styles.tabButtonActive,
          ]}
        >
          <Text
            style={[
              styles.tabLabel,
              activeTab === "journey" && styles.tabLabelActive,
            ]}
          >
            旅程
          </Text>
          {activeTab === "journey" && <View style={styles.tabIndicator} />}
        </Pressable>
        <Pressable
          onPress={() => setActiveTab("therapists")}
          style={[
            styles.tabButton,
            activeTab === "therapists" && styles.tabButtonActive,
          ]}
        >
          <Text
            style={[
              styles.tabLabel,
              activeTab === "therapists" && styles.tabLabelActive,
            ]}
          >
            顾问
          </Text>
          {activeTab === "therapists" && <View style={styles.tabIndicator} />}
        </Pressable>
      </View>
      <View style={styles.content}>
        {activeTab === "chat" && <ChatScreen />}
        {activeTab === "journey" && <JourneyScreen />}
        {activeTab === "therapists" && <TherapistDirectoryScreen />}
      </View>
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
        container: {
          flex: 1,
          backgroundColor: theme.colors.surfaceBackground,
        },
      }),
    [theme],
  );

  if (status === "loading") {
    return (
      <SafeAreaView
        style={[
          styles.container,
          { alignItems: "center", justifyContent: "center" },
        ]}
      >
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {status === "authenticated" ? <AuthenticatedShell /> : <LoginScreen />}
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <AuthProvider>
            <ExpoStatusBar style="dark" />
            <AppShell />
          </AuthProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
