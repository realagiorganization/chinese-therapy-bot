export function ensureUserId(): string {
  const fallback = crypto.randomUUID?.() ?? generateUuidFallback();

  if (typeof window === "undefined") {
    return fallback;
  }

  try {
    const storage = window.localStorage;
    const key = "mindwell:user-id";
    const existing = storage.getItem(key);
    if (existing && existing.trim().length > 0) {
      return existing;
    }
    storage.setItem(key, fallback);
    return fallback;
  } catch {
    return fallback;
  }
}

function generateUuidFallback(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = (Math.random() * 16) | 0;
    const value = character === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}
