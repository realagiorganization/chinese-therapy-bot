import { getAccessToken } from "../auth/tokenStore";

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const envValue = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "";
  if (!envValue || envValue.trim().length === 0) {
    return DEFAULT_BASE_URL;
  }
  return envValue.replace(/\/$/, "");
}

export function withAuthHeaders(
  headers: Record<string, string> = {}
): Record<string, string> {
  const token = getAccessToken();
  if (!token) {
    return headers;
  }
  return {
    ...headers,
    Authorization: `Bearer ${token}`
  };
}
