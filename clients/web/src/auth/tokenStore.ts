type TokenState = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  userId?: string;
};

let currentState: TokenState | null = null;

export function setTokenState(next: TokenState): void {
  currentState = next;
}

export function clearTokenState(): void {
  currentState = null;
}

export function getAccessToken(): string | null {
  return currentState?.accessToken ?? null;
}

export function getRefreshToken(): string | null {
  return currentState?.refreshToken ?? null;
}

export function getExpiresAt(): number | null {
  return currentState?.expiresAt ?? null;
}

export function getUserId(): string | null {
  return currentState?.userId ?? null;
}
