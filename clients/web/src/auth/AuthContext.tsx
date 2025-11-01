import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { clearTokenState, setTokenState } from "./tokenStore";

type AuthTokens = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

type AuthContextValue = {
  status: "loading" | "authenticated" | "unauthenticated";
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  setTokens: (tokens: AuthTokens) => void;
  clearTokens: () => void;
};

const STORAGE_KEY = "mindwell:auth";

function parseStoredTokens(): AuthTokens | null {
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
    return { accessToken, refreshToken, expiresAt };
  } catch {
    return null;
  }
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

type AuthProviderProps = {
  children: React.ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [tokens, setTokensState] = useState<AuthTokens | null>(() => {
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
    setTokensState(next);
    setTokenState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accessToken: next.accessToken,
          refreshToken: next.refreshToken,
          expiresAt: next.expiresAt
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
