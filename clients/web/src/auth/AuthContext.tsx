import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { decodeJwt } from "../utils/jwt";
import { clearTokenState, setTokenState } from "./tokenStore";

type AuthTokens = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

type AuthState = AuthTokens & {
  userId: string;
};

type AuthContextValue = {
  status: "loading" | "authenticated" | "unauthenticated";
  tokens: AuthState | null;
  isAuthenticated: boolean;
  userId: string | null;
  setTokens: (tokens: AuthTokens) => void;
  clearTokens: () => void;
};

const STORAGE_KEY = "mindwell:auth";

function parseStoredTokens(): AuthState | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    const accessToken = typeof parsed?.accessToken === "string" ? parsed.accessToken : null;
    const refreshToken = typeof parsed?.refreshToken === "string" ? parsed.refreshToken : null;
    const expiresAt = Number(parsed?.expiresAt ?? 0);
    if (!accessToken || !refreshToken || Number.isNaN(expiresAt)) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    if (expiresAt <= Date.now()) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    const storedUserId = typeof parsed?.userId === "string" ? parsed.userId.trim() : "";
    const payload = decodeJwt(accessToken);
    const tokenUserId =
      typeof payload?.sub === "string" && payload.sub.trim().length > 0
        ? payload.sub.trim()
        : null;
    const userId = tokenUserId ?? (storedUserId.length > 0 ? storedUserId : null);
    if (!userId) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return { accessToken, refreshToken, expiresAt, userId };
  } catch {
    return null;
  }
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

type AuthProviderProps = {
  children: React.ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [tokens, setTokensState] = useState<AuthState | null>(() => {
    const initial = parseStoredTokens();
    if (initial) {
      setTokenState(initial);
    }
    return initial;
  });
  const [status, setStatus] = useState<"loading" | "authenticated" | "unauthenticated">(
    tokens ? "authenticated" : "unauthenticated"
  );

  const setTokens = useCallback((next: AuthTokens) => {
    const payload = decodeJwt(next.accessToken);
    const userId =
      typeof payload?.sub === "string" && payload.sub.trim().length > 0
        ? payload.sub.trim()
        : null;
    if (!userId) {
      console.warn("Полученный токен не содержит идентификатор пользователя (sub).");
      clearTokenState();
      setTokensState(null);
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(STORAGE_KEY);
      }
      setStatus("unauthenticated");
      return;
    }

    const resolved: AuthState = {
      accessToken: next.accessToken,
      refreshToken: next.refreshToken,
      expiresAt: next.expiresAt,
      userId
    };

    setTokensState(resolved);
    setTokenState(resolved);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accessToken: next.accessToken,
          refreshToken: next.refreshToken,
          expiresAt: next.expiresAt,
          userId
        })
      );
    }
    setStatus("authenticated");
  }, []);

  const clearTokens = useCallback(() => {
    setTokensState(null);
    clearTokenState();
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      tokens,
      isAuthenticated: Boolean(tokens && tokens.expiresAt > Date.now()),
      userId: tokens?.userId ?? null,
      setTokens,
      clearTokens
    }),
    [status, tokens, setTokens, clearTokens]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
