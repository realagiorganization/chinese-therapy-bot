import AsyncStorage from "@react-native-async-storage/async-storage";

import type { ChatMessage } from "../types/chat";
import type { TherapistRecommendation } from "../types/therapists";

const STORAGE_NAMESPACE = "@mindwell/mobile/chat-cache";

type CachedChatPayload = {
  sessionId?: string;
  messages: (ChatMessage & { id: string })[];
  recommendations: TherapistRecommendation[];
  memoryHighlights: { summary: string; keywords: string[] }[];
  updatedAt: number;
  locale?: string;
};

function storageKey(userId: string): string {
  return `${STORAGE_NAMESPACE}/${userId}`;
}

export async function loadChatState(
  userId: string,
): Promise<CachedChatPayload | null> {
  try {
    const raw = await AsyncStorage.getItem(storageKey(userId));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedChatPayload;
    if (!Array.isArray(parsed.messages)) {
      return null;
    }
    return parsed;
  } catch (error) {
    console.warn("Failed to load cached chat state", error);
    return null;
  }
}

export async function persistChatState(
  userId: string,
  state: Omit<CachedChatPayload, "updatedAt">,
): Promise<void> {
  try {
    const payload: CachedChatPayload = {
      ...state,
      updatedAt: Date.now(),
    };
    await AsyncStorage.setItem(storageKey(userId), JSON.stringify(payload));
  } catch (error) {
    console.warn("Failed to persist chat state", error);
  }
}

export async function clearChatState(userId: string | null): Promise<void> {
  if (!userId) {
    return;
  }
  try {
    await AsyncStorage.removeItem(storageKey(userId));
  } catch (error) {
    console.warn("Failed to clear cached chat state", error);
  }
}
