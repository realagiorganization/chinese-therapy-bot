const OAUTH_PENDING_KEY = "mindwell:oauth:pending";

export function setPendingOAuth(status: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (status) {
      window.localStorage.setItem(OAUTH_PENDING_KEY, "1");
    } else {
      window.localStorage.removeItem(OAUTH_PENDING_KEY);
    }
  } catch {
    // ignore storage failures
  }
}

export function isPendingOAuth(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    return window.localStorage.getItem(OAUTH_PENDING_KEY) === "1";
  } catch {
    return false;
  }
}

export function triggerOAuthRedirect(url: string): void {
  if (typeof window !== "undefined" && window.location) {
    window.location.assign(url);
    return;
  }
  if (typeof document !== "undefined" && document.location) {
    document.location.href = url;
  }
}
