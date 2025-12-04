import { apiRequest } from "./api/client";

export type TranslationEntry = {
  key: string;
  text: string;
};

export type TranslationBatchResponse = {
  target_locale: string;
  source_locale: string;
  translations: Record<string, string>;
};

export async function translateBatch({
  targetLocale,
  sourceLocale = "en-US",
  namespace = "mobile",
  entries,
}: {
  targetLocale: string;
  sourceLocale?: string;
  namespace?: string;
  entries: TranslationEntry[];
}): Promise<TranslationBatchResponse> {
  return apiRequest<TranslationBatchResponse>("/translation/batch", {
    method: "POST",
    body: {
      target_locale: targetLocale,
      source_locale: sourceLocale,
      namespace,
      entries,
    },
  });
}
