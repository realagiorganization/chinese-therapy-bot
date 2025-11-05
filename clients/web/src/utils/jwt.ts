export type JwtPayload = {
  sub?: string;
  exp?: number;
  [key: string]: unknown;
};

type BufferModule = {
  from(input: string, encoding: string): { toString(encoding: string): string };
};

let decoder: ((value: string) => string) | null = null;

function base64Decode(value: string): string {
  if (!decoder) {
    if (typeof globalThis.atob === "function") {
      decoder = (input: string) => globalThis.atob!(input);
    } else {
      const maybeBuffer = (globalThis as { Buffer?: BufferModule }).Buffer;
      if (maybeBuffer && typeof maybeBuffer.from === "function") {
        decoder = (input: string) => maybeBuffer.from(input, "base64").toString("utf-8");
      } else {
        throw new Error("Base64 decoder is not available in this environment.");
      }
    }
  }
  return decoder(value);
}

function base64UrlDecode(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  return base64Decode(padded);
}

export function decodeJwt(token: string): JwtPayload | null {
  const segments = token.split(".");
  if (segments.length < 2) {
    return null;
  }

  try {
    const base64 = segments[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const decoded = base64UrlDecode(padded);
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}
