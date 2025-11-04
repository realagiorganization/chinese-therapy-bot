import { getApiBaseUrl } from "./client";
import { asNumber, asRecord, asString } from "./parsing";

export type SmsChallengePayload = {
  challengeId: string;
  expiresIn: number;
  detail: string;
};

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

export async function requestSmsChallenge(options: {
  phoneNumber: string;
  countryCode?: string;
  locale?: string;
}): Promise<SmsChallengePayload> {
  const endpoint = `${getApiBaseUrl()}/api/auth/sms`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      phone_number: options.phoneNumber,
      country_code: options.countryCode ?? "+86",
      locale: options.locale ?? "zh-CN"
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `SMS challenge failed (${response.status}).`);
    throw new Error(detail);
  }

  const payload = asRecord((await response.json()) as unknown) ?? {};
  return {
    challengeId: asString(payload.challenge_id),
    expiresIn: asNumber(payload.expires_in),
    detail: asString(payload.detail)
  };
}

export async function exchangeSmsCode(options: {
  challengeId: string;
  code: string;
  sessionId?: string;
}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/token`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      provider: "sms",
      challenge_id: options.challengeId,
      code: options.code,
      session_id: options.sessionId ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `Verification failed (${response.status}).`);
    throw new Error(detail);
  }

  const payload = asRecord((await response.json()) as unknown) ?? {};
  return {
    accessToken: asString(payload.access_token),
    refreshToken: asString(payload.refresh_token),
    expiresIn: asNumber(payload.expires_in),
    tokenType: asString(payload.token_type, "bearer") || "bearer"
  };
}

export async function exchangeGoogleCode(options: {
  code: string;
  redirectUri?: string;
  sessionId?: string;
}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/token`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      provider: "google",
      code: options.code,
      redirect_uri: options.redirectUri ?? null,
      session_id: options.sessionId ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `Google login failed (${response.status}).`);
    throw new Error(detail);
  }

  const payload = asRecord((await response.json()) as unknown) ?? {};
  return {
    accessToken: asString(payload.access_token),
    refreshToken: asString(payload.refresh_token),
    expiresIn: asNumber(payload.expires_in),
    tokenType: asString(payload.token_type, "bearer") || "bearer"
  };
}

export async function exchangeWeChatCode(options: {
  code: string;
  sessionId?: string;
  redirectUri?: string;
}): Promise<TokenPair> {
  const endpoint = `${getApiBaseUrl()}/api/auth/token`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      provider: "wechat",
      code: options.code,
      session_id: options.sessionId ?? null,
      redirect_uri: options.redirectUri ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `WeChat login failed (${response.status}).`);
    throw new Error(detail);
  }

  const payload = asRecord((await response.json()) as unknown) ?? {};
  return {
    accessToken: asString(payload.access_token),
    refreshToken: asString(payload.refresh_token),
    expiresIn: asNumber(payload.expires_in),
    tokenType: asString(payload.token_type, "bearer") || "bearer"
  };
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
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      refresh_token: options.refreshToken,
      session_id: options.sessionId ?? null,
      user_agent: options.userAgent ?? null,
      ip_address: options.ipAddress ?? null
    })
  });

  if (!response.ok) {
    const payload = asRecord(await parseJson(response));
    const detail = asString(payload?.detail, `Token refresh failed (${response.status}).`);
    throw new Error(detail);
  }

  const payload = asRecord((await response.json()) as unknown) ?? {};
  return {
    accessToken: asString(payload.access_token),
    refreshToken: asString(payload.refresh_token),
    expiresIn: asNumber(payload.expires_in),
    tokenType: asString(payload.token_type, "bearer") || "bearer"
  };
}
