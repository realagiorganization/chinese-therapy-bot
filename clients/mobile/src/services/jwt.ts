export type JwtPayload = {
  sub?: string;
  exp?: number;
  [key: string]: unknown;
};

let decodeFn: ((value: string) => string) | null = null;

function base64Decode(value: string): string {
  if (!decodeFn) {
    if (typeof globalThis.atob === "function") {
      decodeFn = (input: string) => globalThis.atob!(input);
    } else {
      // eslint-disable-next-line @typescript-eslint/no-var-requires -- fallback only executed in environments without atob
      const base64 = require("base-64") as {
        decode: (input: string) => string;
      };
      decodeFn = base64.decode;
    }
  }
  return decodeFn(value);
}

export function decodeJwt(token: string): JwtPayload | null {
  const segments = token.split(".");
  if (segments.length < 2) {
    return null;
  }
  try {
    const base64 = segments[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    const json = base64Decode(padded);
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}
