import { getApiBaseUrl, withAuthHeaders } from "./client";

export type TranscriptionResponse = {
  text: string;
  language: string;
};

function deriveFileExtension(mimeType: string) {
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  if (mimeType.includes("mp4") || mimeType.includes("mpeg")) {
    return "mp4";
  }
  return "webm";
}

export async function transcribeAudio(blob: Blob, locale: string): Promise<TranscriptionResponse> {
  const endpoint = `${getApiBaseUrl()}/api/voice/transcribe?language=${encodeURIComponent(locale)}`;
  const formData = new FormData();
  const extension = deriveFileExtension(blob.type || "audio/webm");
  formData.append("audio", blob, `recording.${extension}`);

  const response = await fetch(endpoint, {
    method: "POST",
    headers: withAuthHeaders(),
    body: formData
  });

  if (!response.ok) {
    let detail = `ASR request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // fall through
    }
    throw new Error(detail);
  }

  const payload = (await response.json()) as TranscriptionResponse;
  return payload;
}
