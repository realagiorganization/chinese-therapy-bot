import { getAccessToken } from "../auth/tokenStore";

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const envValue = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "";
  if (!envValue || envValue.trim().length === 0) {
    return DEFAULT_BASE_URL;
  }
  return envValue.replace(/\/$/, "");
}

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

function deriveProxyBaseUrlFromApi(apiBaseUrl: string): string {
  try {
    const parsed = new URL(apiBaseUrl);
    const trimmedPath = parsed.pathname.replace(/\/+$/, "");
    let targetPath = trimmedPath;

    if (targetPath.endsWith("/api")) {
      targetPath = targetPath.slice(0, -4);
    }

    if (targetPath.length === 0 || targetPath === "/") {
      return parsed.origin;
    }

    return `${parsed.origin}${
      targetPath.startsWith("/") ? targetPath : `/${targetPath}`
    }`;
  } catch {
    return apiBaseUrl.replace(/\/api$/, "");
  }
}

export function getAuthProxyBaseUrl(): string {
  const envValue =
    (import.meta.env?.VITE_AUTH_PROXY_BASE_URL as string | undefined) ?? "";
  if (envValue && envValue.trim().length > 0) {
    return normalizeBaseUrl(envValue);
  }

  const apiBase = getApiBaseUrl();
  return normalizeBaseUrl(deriveProxyBaseUrlFromApi(apiBase));
}

export function getAuthProxyUrl(pathname: string): string {
  const base = getAuthProxyBaseUrl();
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return `${base}${normalizedPath}`;
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
