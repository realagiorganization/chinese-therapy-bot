import { AuthProvider, useAuth } from "@context/AuthContext";
import { usePushNotifications } from "@hooks/usePushNotifications";
import { ChatScreen } from "@screens/ChatScreen";
import { LoginScreen } from "@screens/LoginScreen";
import { ThemeProvider, useTheme } from "@theme/ThemeProvider";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import { useMemo } from "react";
import { ActivityIndicator, SafeAreaView, StyleSheet } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

function AppShell() {
  const { status, userId } = useAuth();
  const theme = useTheme();
  usePushNotifications(status === "authenticated" ? userId : null);

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
      {status === "authenticated" ? <ChatScreen /> : <LoginScreen />}
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider>
          <ExpoStatusBar style="dark" />
          <AppShell />
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
