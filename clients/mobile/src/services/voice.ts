import type { PlatformOSType } from "react-native";

import { ApiError, getBaseUrl } from "./api/client";

export type TranscriptionResponse = {
  text: string;
  language: string;
};

type TranscribeParams = {
  blob: Blob;
  locale: string;
  accessToken: string;
};

const DEFAULT_MIME_TYPE = "audio/webm";
const MIME_FALLBACKS: Partial<Record<PlatformOSType, string>> = {
  ios: "audio/m4a",
  android: "audio/webm",
  macos: "audio/webm",
  windows: "audio/webm",
  web: "audio/webm",
  native: "audio/webm",
};

function coerceMimeType(blob: Blob, platform: PlatformOSType): string {
  if (blob.type && blob.type !== "application/octet-stream") {
    return blob.type;
  }
  return MIME_FALLBACKS[platform] ?? DEFAULT_MIME_TYPE;
}

function resolveFileExtension(mimeType: string): string {
  if (mimeType.includes("webm")) {
    return "webm";
  }
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  if (mimeType.includes("wav")) {
    return "wav";
  }
  if (mimeType.includes("3gp")) {
    return "3gp";
  }
  return "m4a";
}

export async function transcribeRecording(
  { blob, locale, accessToken }: TranscribeParams,
  platform: PlatformOSType,
): Promise<TranscriptionResponse> {
  const apiBase = getBaseUrl().replace(/\/$/, "");
  const endpoint = `${apiBase}/voice/transcribe?language=${encodeURIComponent(locale)}`;

  const mimeType = coerceMimeType(blob, platform);
  const typedBlob =
    blob.type && blob.type !== "application/octet-stream"
      ? blob
      : blob.slice(0, blob.size, mimeType);
  const formData = new FormData();
  formData.append(
    "audio",
    typedBlob,
    `recording.${resolveFileExtension(mimeType)}`,
  );

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  if (!response.ok) {
    let detail =
      response.statusText || `ASR request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = payload.detail;
      }
    } catch {
      // ignore JSON parsing errors and keep fallback detail
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as TranscriptionResponse;
}
