type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getBaseUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (envUrl && envUrl.length > 0) {
    return envUrl.endsWith("/") ? envUrl.slice(0, -1) : envUrl;
  }
  return "http://localhost:8000/api";
}

export async function apiRequest<T>(
  path: string,
  { method = "GET", headers = {}, body, signal }: RequestOptions = {},
): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const init: RequestInit = {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...headers,
    },
    signal,
  };

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const response = await fetch(url, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // ignore parse errors, fall back to status text
    }
    throw new ApiError(detail, response.status);
  }

  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return (await response.json()) as T;
  }
  // @ts-expect-error - allow void responses
  return undefined;
}
