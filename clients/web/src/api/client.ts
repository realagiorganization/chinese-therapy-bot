const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const envValue = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "";
  if (!envValue || envValue.trim().length === 0) {
    return DEFAULT_BASE_URL;
  }
  return envValue.replace(/\/$/, "");
}
