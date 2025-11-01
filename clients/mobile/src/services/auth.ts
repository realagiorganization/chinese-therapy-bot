import { apiRequest } from "./api/client";

export type SmsChallengeRequest = {
  phoneNumber: string;
  countryCode: string;
  locale?: string;
};

export type SmsChallengeResponse = {
  challengeId: string;
  expiresIn: number;
  detail: string;
};

export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
};

export async function requestSmsChallenge(
  payload: SmsChallengeRequest,
): Promise<SmsChallengeResponse> {
  const response = await apiRequest<{
    challenge_id: string;
    expires_in: number;
    detail: string;
  }>("/auth/sms", {
    method: "POST",
    body: {
      phone_number: payload.phoneNumber,
      country_code: payload.countryCode,
      locale: payload.locale ?? "zh-CN",
    },
  });

  return {
    challengeId: response.challenge_id,
    expiresIn: response.expires_in,
    detail: response.detail,
  };
}

export async function exchangeSmsCode(params: {
  challengeId: string;
  code: string;
}): Promise<TokenResponse> {
  const response = await apiRequest<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }>("/auth/token", {
    method: "POST",
    body: {
      provider: "sms",
      code: params.code,
      challenge_id: params.challengeId,
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
}): Promise<TokenResponse> {
  const response = await apiRequest<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }>("/auth/token", {
    method: "POST",
    body: {
      provider: "google",
      code: params.code,
      redirect_uri: params.redirectUri,
    },
  });

  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    tokenType: response.token_type,
    expiresIn: response.expires_in,
  };
}
