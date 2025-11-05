import { getApiBaseUrl, withAuthHeaders } from "./client";
import { asArray, asRecord, asString, asStringArray } from "./parsing";
import type { ChatTemplate, ChatTemplatesResponse } from "./types";

type LoadOptions = {
  locale?: string;
  topic?: string | null;
  keywords?: string[];
  limit?: number;
  signal?: AbortSignal;
};

function normalizeTemplate(payload: unknown): ChatTemplate | null {
  const data = asRecord(payload);
  if (!data) {
    return null;
  }

  const followUps = data.followUpQuestions ?? data.follow_up_questions;
  const tips = data.selfCareTips ?? data.self_care_tips;

  return {
    id: asString(data.id),
    topic: asString(data.topic),
    locale: asString(data.locale),
    title: asString(data.title),
    userPrompt: asString(data.userPrompt ?? data.user_prompt),
    assistantExample: asString(data.assistantExample ?? data.assistant_example),
    followUpQuestions: asStringArray(followUps),
    selfCareTips: asStringArray(tips),
    keywords: asStringArray(data.keywords),
    tags: asStringArray(data.tags)
  };
}

export async function loadChatTemplates(options: LoadOptions = {}): Promise<ChatTemplatesResponse> {
  const endpoint = new URL(`${getApiBaseUrl()}/api/chat/templates`);
  if (options.locale) {
    endpoint.searchParams.set("locale", options.locale);
  }
  if (options.topic) {
    endpoint.searchParams.set("topic", options.topic);
  }
  if (options.keywords && options.keywords.length > 0) {
    for (const keyword of options.keywords) {
      endpoint.searchParams.append("keywords", keyword);
    }
  }
  if (options.limit) {
    endpoint.searchParams.set("limit", String(options.limit));
  }

  const response = await fetch(endpoint, {
    credentials: "include",
    headers: withAuthHeaders({
      Accept: "application/json"
    }),
    signal: options.signal
  });

  if (!response.ok) {
    throw new Error(`Failed to load chat templates (status ${response.status}).`);
  }

  const payload = await response.json();
  const data = asRecord(payload) ?? {};

  return {
    locale: asString(data.locale),
    topics: asStringArray(data.topics),
    templates: asArray(data.templates, normalizeTemplate)
  };
}
