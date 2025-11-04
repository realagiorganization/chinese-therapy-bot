import { getApiBaseUrl } from "./client";
import { asNumber, asRecord, asString } from "./parsing";

export class AuthError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "AuthError";
  }
}

export type TokenPair = {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  tokenType: string;
};

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function buildAuthHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Accept: "application/json"
  };
}

function buildBody(payload: Record<string, unknown>): string {
  return JSON.stringify(payload);
}

function normalizeTokenResponse(payload: Record<string, unknown> | null | undefined): TokenPair {
  const data = payload ?? {};
  return {
    accessToken: asString(data.access_token),
    refreshToken: asString(data.refresh_token),
    expiresIn: asNumber(data.expires_in),
    tokenType: asString(data.token_type, "bearer") || "bearer"
  };
}

export async function exchangeOAuthSession(options: {
  sessionId?: string;
  userAgent?: string;
  ipAddress?: string;
} = {}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/session`;
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers: buildAuthHeaders(),
    body: buildBody({
      session_id: options.sessionId ?? null,
      user_agent: options.userAgent ?? null,
      ip_address: options.ipAddress ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `OAuth session exchange failed (${response.status}).`);
    throw new AuthError(detail, response.status);
  }

  const payload = asRecord((await response.json()) as unknown);
  return normalizeTokenResponse(payload);
}

export async function loginWithDemoCode(options: {
  code: string;
  sessionId?: string;
  userAgent?: string;
  ipAddress?: string;
}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/demo`;
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers: buildAuthHeaders(),
    body: buildBody({
      code: options.code,
      session_id: options.sessionId ?? null,
      user_agent: options.userAgent ?? null,
      ip_address: options.ipAddress ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `Demo login failed (${response.status}).`);
    throw new AuthError(detail, response.status);
  }

  const payload = asRecord((await response.json()) as unknown);
  return normalizeTokenResponse(payload);
}

export async function refreshToken(options: {
  refreshToken: string;
  sessionId?: string;
  userAgent?: string;
  ipAddress?: string;
}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/token/refresh`;
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers: buildAuthHeaders(),
    body: buildBody({
      refresh_token: options.refreshToken,
      session_id: options.sessionId ?? null,
      user_agent: options.userAgent ?? null,
      ip_address: options.ipAddress ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `Token refresh failed (${response.status}).`);
    throw new AuthError(detail, response.status);
  }

  const payload = asRecord((await response.json()) as unknown);
  return normalizeTokenResponse(payload);
}
