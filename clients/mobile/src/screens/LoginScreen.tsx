import { useAuth } from "@context/AuthContext";
import { useTheme } from "@theme/ThemeProvider";
import { useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

function Button({
  onPress,
  label,
  disabled,
  loading,
}: {
  onPress: () => void;
  label: string;
  disabled?: boolean;
  loading?: boolean;
}) {
  const theme = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        button: {
          backgroundColor: theme.colors.primary,
          opacity: disabled ? 0.5 : 1,
          paddingVertical: theme.spacing.md,
          borderRadius: theme.radius.md,
          alignItems: "center",
          justifyContent: "center",
          shadowColor: "#000",
          shadowOpacity: 0.1,
          shadowOffset: { width: 0, height: 2 },
          shadowRadius: 4,
          elevation: 2,
        },
        label: {
          color: "#fff",
          fontWeight: "600",
          fontSize: 16,
        },
      }),
    [theme, disabled],
  );

  return (
    <Pressable onPress={onPress} disabled={disabled} style={styles.button}>
      <Text style={styles.label}>{loading ? "…" : label}</Text>
    </Pressable>
  );
}

export function LoginScreen() {
  const {
    requestSms,
    verifySms,
    loginWithGoogle,
    isRequestingSms,
    isVerifying,
    challenge,
    error,
  } = useAuth();
  const theme = useTheme();

  const [countryCode, setCountryCode] = useState("+86");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [googleCode, setGoogleCode] = useState("");

  const hasActiveChallenge = useMemo(() => {
    if (!challenge) {
      return false;
    }
    return challenge.expiresAt > Date.now();
  }, [challenge]);

  const hint = useMemo(() => {
    if (!challenge || !hasActiveChallenge) {
      return null;
    }
    const remainingSeconds = Math.max(
      0,
      Math.round((challenge.expiresAt - Date.now()) / 1000),
    );
    return `验证码已发送，${remainingSeconds} 秒后过期`;
  }, [challenge, hasActiveChallenge]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: theme.colors.surfaceBackground,
        },
        card: {
          backgroundColor: theme.colors.surfaceCard,
          margin: theme.spacing.lg,
          padding: theme.spacing.lg,
          borderRadius: theme.radius.lg,
          gap: theme.spacing.md,
          shadowColor: "#000",
          shadowOpacity: 0.08,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 4 },
          elevation: 3,
        },
        heading: {
          fontSize: 24,
          fontWeight: "600",
          color: theme.colors.textPrimary,
        },
        subtitle: {
          fontSize: 16,
          color: theme.colors.textSecondary,
        },
        label: {
          fontSize: 14,
          fontWeight: "600",
          color: theme.colors.textSecondary,
        },
        row: {
          flexDirection: "row",
          gap: theme.spacing.sm,
        },
        input: {
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          borderRadius: theme.radius.md,
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          fontSize: 16,
          color: theme.colors.textPrimary,
          flex: 1,
        },
        error: {
          color: theme.colors.danger,
          fontSize: 14,
        },
        hint: {
          color: theme.colors.textSecondary,
          fontSize: 14,
        },
        sectionGap: {
          gap: theme.spacing.sm,
        },
        divider: {
          height: 1,
          backgroundColor: theme.colors.surfaceMuted,
        },
      }),
    [theme],
  );

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}
      >
        <View style={styles.card}>
          <View style={styles.sectionGap}>
            <Text style={styles.heading}>MindWell 登录</Text>
            <Text style={styles.subtitle}>
              使用短信验证码或 Google 登录继续体验。
            </Text>
          </View>

          <View style={styles.sectionGap}>
            <Text style={styles.label}>短信验证码</Text>
            <View style={styles.row}>
              <TextInput
                value={countryCode}
                onChangeText={setCountryCode}
                style={[styles.input, { flex: 0.4 }]}
                placeholder="+86"
                keyboardType="phone-pad"
              />
              <TextInput
                value={phoneNumber}
                onChangeText={setPhoneNumber}
                style={styles.input}
                placeholder="手机号"
                keyboardType="phone-pad"
              />
            </View>
            <Button
              label="发送验证码"
              onPress={() => requestSms(phoneNumber, countryCode)}
              disabled={isRequestingSms || phoneNumber.trim().length === 0}
              loading={isRequestingSms}
            />
            {hint && <Text style={styles.hint}>{hint}</Text>}
            <TextInput
              value={verificationCode}
              onChangeText={setVerificationCode}
              style={styles.input}
              placeholder="输入验证码"
              keyboardType="number-pad"
            />
            <Button
              label="验证并登录"
              onPress={() => verifySms(verificationCode)}
              disabled={
                !hasActiveChallenge ||
                isVerifying ||
                verificationCode.trim().length === 0
              }
              loading={isVerifying}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.sectionGap}>
            <Text style={styles.label}>Google 登录</Text>
            <TextInput
              value={googleCode}
              onChangeText={setGoogleCode}
              style={styles.input}
              placeholder="授权码"
              autoCapitalize="none"
            />
            <Button
              label="使用 Google 登录"
              onPress={() => loginWithGoogle(googleCode)}
              disabled={googleCode.trim().length === 0 || isVerifying}
              loading={isVerifying}
            />
          </View>

          {error && <Text style={styles.error}>{error}</Text>}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
