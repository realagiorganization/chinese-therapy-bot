import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    title: "四步呼吸练习",
    description: "快速缓解焦虑。",
    durationMinutes: 5,
    cadenceLabel: "4-7-8",
    steps: [],
    recommendedFrequency: "睡前练习",
    ctaLabel: "开始",
    ctaAction: "/breathing"
  },
  {
    id: "trending",
    moduleType: "trending_topics",
    title: "热门主题",
    description: "近期焦点",
    topics: [{ name: "压力管理", momentum: 68, trend: "up", summary: "继续保持呼吸练习。" }],
    insights: ["保持规律作息"],
    ctaLabel: "查看建议",
    ctaAction: "/trends"
  }
] as ExploreModule[];

describe("useExploreModules", () => {
  beforeEach(() => {
    mocks.loadExploreModules.mockReset();
    mocks.loadExploreModules.mockResolvedValue({
      locale: "zh-CN",
      modules: SAMPLE_MODULES,
      evaluatedFlags: { explore_breathing: true, explore_trending: true },
      source: "api"
    });
  });

  it("loads modules and exposes evaluated feature flags", async () => {
    const { result } = renderHook(() => useExploreModules("zh-CN"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.modules).toHaveLength(2);
    expect(result.current.source).toBe("api");
    expect(result.current.evaluatedFlags.explore_breathing).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("falls back gracefully when the API request fails", async () => {
    mocks.loadExploreModules.mockRejectedValueOnce(new Error("network"));
    const { result } = renderHook(() => useExploreModules("en-US"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.modules).toEqual([]);
    expect(result.current.source).toBe("fallback");
    expect(result.current.error).not.toBeNull();
  });
});
