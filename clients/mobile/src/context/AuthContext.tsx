import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  exchangeGoogleCode,
  exchangeSmsCode,
  exchangeWeChatCode,
  requestSmsChallenge,
  type SmsChallengeResponse,
  type TokenResponse,
} from "@services/auth";
import { clearChatState } from "@services/chatCache";
import { decodeJwt } from "@services/jwt";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { v4 as uuidv4 } from "uuid";

type AuthStatus = "loading" | "unauthenticated" | "authenticated";

type TokenState = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

type ChallengeState = {
  challengeId: string;
  detail: string;
  expiresAt: number;
};

type AuthContextValue = {
  status: AuthStatus;
  tokens: TokenState | null;
  userId: string | null;
  challenge: ChallengeState | null;
  isRequestingSms: boolean;
  isVerifying: boolean;
  error: string | null;
  requestSms: (
    phoneNumber: string,
    countryCode: string,
    locale?: string,
  ) => Promise<void>;
  verifySms: (code: string) => Promise<void>;
  loginWithGoogle: (code: string, redirectUri?: string) => Promise<void>;
  loginWithWeChat: (code: string, redirectUri?: string) => Promise<void>;
  logout: () => Promise<void>;
};

const STORAGE_KEY = "@mindwell/mobile/tokens";

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

function computeExpiry(expiresIn: number): number {
  const ttlSeconds =
    Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : 3600;
  return Date.now() + ttlSeconds * 1000;
}

function deriveUserId(tokens: TokenState): string {
  const payload = decodeJwt(tokens.accessToken);
  if (payload?.sub && typeof payload.sub === "string") {
    return payload.sub;
  }
  return uuidv4();
}

async function persistTokens(tokens: TokenState | null): Promise<void> {
  if (!tokens) {
    await AsyncStorage.removeItem(STORAGE_KEY);
    return;
  }
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}

function toTokenState(response: TokenResponse): TokenState {
  return {
    accessToken: response.accessToken,
    refreshToken: response.refreshToken,
    expiresAt: computeExpiry(response.expiresIn),
  };
}

function toChallengeState(response: SmsChallengeResponse): ChallengeState {
  return {
    challengeId: response.challengeId,
    detail: response.detail,
    expiresAt: computeExpiry(response.expiresIn),
  };
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [tokens, setTokens] = useState<TokenState | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [challenge, setChallenge] = useState<ChallengeState | null>(null);
  const [isRequestingSms, setRequestingSms] = useState(false);
  const [isVerifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const bootstrap = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (!stored) {
          if (isMounted) {
            setStatus("unauthenticated");
          }
          return;
        }
        const parsed = JSON.parse(stored) as TokenState;
        if (parsed.expiresAt <= Date.now()) {
          await AsyncStorage.removeItem(STORAGE_KEY);
          if (isMounted) {
            setStatus("unauthenticated");
          }
          return;
        }
        if (isMounted) {
          setTokens(parsed);
          setUserId(deriveUserId(parsed));
          setStatus("authenticated");
        }
      } catch (err) {
        console.warn("Failed to restore auth state", err);
        if (isMounted) {
          setStatus("unauthenticated");
        }
      }
    };
    bootstrap();
    return () => {
      isMounted = false;
    };
  }, []);

  const requestSms = useCallback(
    async (
      phoneNumber: string,
      countryCode: string,
      locale: string = "zh-CN",
    ) => {
      setRequestingSms(true);
      setError(null);
      try {
        const response = await requestSmsChallenge({
          phoneNumber,
          countryCode,
          locale,
        });
        setChallenge(toChallengeState(response));
      } catch (err) {
        console.warn("Failed to request SMS challenge", err);
        setError(
          err instanceof Error
            ? err.message
            : "Failed to request SMS challenge.",
        );
        setChallenge(null);
      } finally {
        setRequestingSms(false);
      }
    },
    [],
  );

  const verifySms = useCallback(
    async (code: string) => {
      if (!challenge) {
        setError("No active challenge. Please request a new SMS code.");
        return;
      }
      if (challenge.expiresAt <= Date.now()) {
        setError("Verification code expired. Request a new one.");
        setChallenge(null);
        return;
      }
      setVerifying(true);
      setError(null);
      try {
        const response = await exchangeSmsCode({
          challengeId: challenge.challengeId,
          code,
        });
        const nextTokens = toTokenState(response);
        setTokens(nextTokens);
        setUserId(deriveUserId(nextTokens));
        setStatus("authenticated");
        setChallenge(null);
        await persistTokens(nextTokens);
      } catch (err) {
        console.warn("SMS verification failed", err);
        setError(
          err instanceof Error ? err.message : "Failed to verify SMS code.",
        );
      } finally {
        setVerifying(false);
      }
    },
    [challenge],
  );

  const loginWithGoogle = useCallback(
    async (code: string, redirectUri?: string) => {
      setVerifying(true);
      setError(null);
      try {
        const response = await exchangeGoogleCode({ code, redirectUri });
        const nextTokens = toTokenState(response);
        setTokens(nextTokens);
        setUserId(deriveUserId(nextTokens));
        setStatus("authenticated");
        await persistTokens(nextTokens);
      } catch (err) {
        console.warn("Google login failed", err);
        setError(err instanceof Error ? err.message : "Google login failed.");
      } finally {
        setVerifying(false);
      }
    },
    [],
  );

  const loginWithWeChat = useCallback(
    async (code: string, redirectUri?: string) => {
      setVerifying(true);
      setError(null);
      try {
        const response = await exchangeWeChatCode({ code, redirectUri });
        const nextTokens = toTokenState(response);
        setTokens(nextTokens);
        setUserId(deriveUserId(nextTokens));
        setStatus("authenticated");
        await persistTokens(nextTokens);
      } catch (err) {
        console.warn("WeChat login failed", err);
        setError(
          err instanceof Error ? err.message : "WeChat login failed.",
        );
      } finally {
        setVerifying(false);
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    const currentUserId = userId;
    setTokens(null);
    setUserId(null);
    setChallenge(null);
    setStatus("unauthenticated");
    setError(null);
    await persistTokens(null);
    await clearChatState(currentUserId);
  }, [userId]);

  useEffect(() => {
    persistTokens(tokens).catch((error) => {
      console.warn("Failed to sync tokens to storage", error);
    });
  }, [tokens]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      tokens,
      userId,
      challenge,
      isRequestingSms,
      isVerifying,
      error,
      requestSms,
      verifySms,
      loginWithGoogle,
      loginWithWeChat,
      logout,
    }),
    [
      status,
      tokens,
      userId,
      challenge,
      isRequestingSms,
      isVerifying,
      error,
      requestSms,
      verifySms,
      loginWithGoogle,
      loginWithWeChat,
      logout,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return ctx;
}
