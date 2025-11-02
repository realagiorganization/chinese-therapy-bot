import { useNetworkStatus } from "@hooks/useNetworkStatus";
import { useTheme } from "@theme/ThemeProvider";
import { memo, useMemo } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

type ConnectivityBannerProps = {
  placement?: "top" | "bottom";
};

function ConnectivityBannerComponent({
  placement = "top",
}: ConnectivityBannerProps) {
  const { isConnected, isInternetReachable } = useNetworkStatus();
  const theme = useTheme();
  const insets = useSafeAreaInsets();

  const visible = !isConnected || !isInternetReachable;
  const containerStyles = useMemo(() => {
    const baseSpacing =
      placement === "top" ? insets.top : Math.max(insets.bottom, 8);
    return StyleSheet.create({
      container: {
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        paddingTop: placement === "top" ? baseSpacing : theme.spacing.sm,
        paddingBottom: placement === "bottom" ? baseSpacing : theme.spacing.sm,
        paddingHorizontal: theme.spacing.lg,
        alignItems: "center",
        justifyContent: "center",
        borderBottomLeftRadius: placement === "top" ? 0 : theme.radius.md,
        borderBottomRightRadius: placement === "top" ? 0 : theme.radius.md,
        borderTopLeftRadius: placement === "bottom" ? 0 : theme.radius.md,
        borderTopRightRadius: placement === "bottom" ? 0 : theme.radius.md,
      },
      text: {
        color: theme.colors.danger,
        fontSize: 13,
        fontWeight: "500",
        textAlign: "center",
      },
    });
  }, [
    placement,
    theme.colors.danger,
    theme.spacing.lg,
    theme.spacing.sm,
    theme.radius.md,
    insets.bottom,
    insets.top,
  ]);

  if (!visible) {
    return null;
  }

  const message =
    Platform.OS === "ios"
      ? "当前处于离线状态，最近的对话将继续离线保存。"
      : "离线模式已启用，语音与推荐将在联网后恢复。";

  return (
    <View style={containerStyles.container}>
      <Text accessibilityRole="text" style={containerStyles.text}>
        {message}
      </Text>
    </View>
  );
}

export const ConnectivityBanner = memo(ConnectivityBannerComponent);
