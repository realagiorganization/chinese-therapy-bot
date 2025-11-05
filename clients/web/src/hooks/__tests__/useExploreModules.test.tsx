import { renderHook, waitFor } from "@testing-library/react";
import { Buffer } from "node:buffer";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../auth/AuthContext";
import type { ExploreModule } from "../../api/types";
import { useExploreModules } from "../useExploreModules";

const mocks = vi.hoisted(() => ({
  loadExploreModules: vi.fn()
}));

vi.mock("../../api/explore", () => ({
  loadExploreModules: mocks.loadExploreModules
}));

const SAMPLE_MODULES: ExploreModule[] = [
  {
    id: "breathing",
    moduleType: "breathing_exercise",
    title: "Four-step breathing reset",
    description: "A quick routine to ease anxious spikes.",
    durationMinutes: 5,
    cadenceLabel: "4-7-8",
    steps: [],
    recommendedFrequency: "Practice before bed",
    ctaLabel: "Begin",
    ctaAction: "/breathing"
  },
  {
    id: "trending",
    moduleType: "trending_topics",
    title: "Popular themes",
    description: "Highlights from recent sessions.",
    topics: [
      { name: "Stress management", momentum: 68, trend: "up", summary: "Keep pairing it with your breathing work." }
    ],
    insights: ["Maintain a consistent wind-down routine"],
    ctaLabel: "View suggestions",
    ctaAction: "/trends"
  }
] as ExploreModule[];

const TEST_USER_ID = "11111111-1111-1111-1111-111111111111";

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

function seedAuthStorage(): void {
  const expiresAt = Date.now() + 60 * 60 * 1000;
  const token = buildJwt({ sub: TEST_USER_ID, exp: Math.floor(expiresAt / 1000) });
  window.localStorage.setItem(
    "mindwell:auth",
    JSON.stringify({
      accessToken: token,
      refreshToken: "refresh-token",
      expiresAt,
      userId: TEST_USER_ID
    })
  );
}

function withAuthProvider({ children }: PropsWithChildren): JSX.Element {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useExploreModules", () => {
  beforeEach(() => {
    window.localStorage.clear();
    seedAuthStorage();
    mocks.loadExploreModules.mockReset();
    mocks.loadExploreModules.mockResolvedValue({
      locale: "en-US",
      modules: SAMPLE_MODULES,
      evaluatedFlags: { explore_breathing: true, explore_trending: true },
      source: "api"
    });
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("loads modules and exposes evaluated feature flags", async () => {
    const { result } = renderHook(() => useExploreModules("en-US"), {
      wrapper: withAuthProvider
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.modules).toHaveLength(2);
    expect(result.current.source).toBe("api");
    expect(result.current.evaluatedFlags.explore_breathing).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("falls back gracefully when the API request fails", async () => {
    mocks.loadExploreModules.mockRejectedValueOnce(new Error("network"));
    const { result } = renderHook(() => useExploreModules("en-US"), {
      wrapper: withAuthProvider
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.modules).toEqual([]);
    expect(result.current.source).toBe("fallback");
    expect(result.current.error).not.toBeNull();
  });
});
