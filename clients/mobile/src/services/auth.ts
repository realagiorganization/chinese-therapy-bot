import { apiRequest } from "./api/client";

export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
};

export async function loginWithDemoCode(params: {
  code: string;
  sessionId?: string;
  userAgent?: string;
  ipAddress?: string;
}): Promise<TokenResponse> {
  const response = await apiRequest<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }>("/auth/demo", {
    method: "POST",
    body: {
      code: params.code,
      session_id: params.sessionId,
      user_agent: params.userAgent,
      ip_address: params.ipAddress,
    },
  });

  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    tokenType: response.token_type,
    expiresIn: response.expires_in,
  };
}

export async function exchangeGoogleCode(params: {
  code: string;
  redirectUri?: string;
  sessionId?: string;
  userAgent?: string;
  ipAddress?: string;
}): Promise<TokenResponse> {
  const response = await apiRequest<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }>("/auth/google", {
    method: "POST",
    body: {
      code: params.code,
      redirect_uri: params.redirectUri,
      session_id: params.sessionId,
      user_agent: params.userAgent,
      ip_address: params.ipAddress,
    },
  });

  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    tokenType: response.token_type,
    expiresIn: response.expires_in,
  };
}
