import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  exchangeGoogleCode,
  loginWithDemoCode,
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

type AuthContextValue = {
  status: AuthStatus;
  tokens: TokenState | null;
  userId: string | null;
  isAuthenticating: boolean;
  error: string | null;
  loginWithDemoCode: (code: string) => Promise<void>;
  loginWithGoogle: (code: string, redirectUri?: string) => Promise<void>;
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

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [tokens, setTokens] = useState<TokenState | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isAuthenticating, setAuthenticating] = useState(false);
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

  const handleLoginSuccess = useCallback((nextTokens: TokenState) => {
    setTokens(nextTokens);
    setUserId(deriveUserId(nextTokens));
    setStatus("authenticated");
  }, []);

  const loginWithDemo = useCallback(
    async (code: string) => {
      setAuthenticating(true);
      setError(null);
      try {
        const response = await loginWithDemoCode({ code });
        const nextTokens = toTokenState(response);
        handleLoginSuccess(nextTokens);
        await persistTokens(nextTokens);
      } catch (err) {
        console.warn("Demo login failed", err);
        setError(
          err instanceof Error
            ? err.message
            : "Demo login failed. Please try again.",
        );
      } finally {
        setAuthenticating(false);
      }
    },
    [handleLoginSuccess],
  );

  const loginWithGoogle = useCallback(
    async (code: string, redirectUri?: string) => {
      setAuthenticating(true);
      setError(null);
      try {
        const response = await exchangeGoogleCode({ code, redirectUri });
        const tokens = toTokenState(response);
        handleLoginSuccess(tokens);
        await persistTokens(tokens);
      } catch (err) {
        console.warn("Google login failed", err);
        setError(err instanceof Error ? err.message : "Google login failed.");
      } finally {
        setAuthenticating(false);
      }
    },
    [handleLoginSuccess],
  );

  const logout = useCallback(async () => {
    const currentUserId = userId;
    setTokens(null);
    setUserId(null);
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
      isAuthenticating,
      error,
      loginWithDemoCode: loginWithDemo,
      loginWithGoogle,
      logout,
    }),
    [
      status,
      tokens,
      userId,
      isAuthenticating,
      error,
      loginWithDemo,
      loginWithGoogle,
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
