import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JourneyReportsPayload } from "../../api/reports";
import { useJourneyReports } from "../useJourneyReports";

const mocks = vi.hoisted(() => ({
  loadJourneyReports: vi.fn(),
  ensureUserId: vi.fn()
}));

vi.mock("../../api/reports", () => ({
  loadJourneyReports: mocks.loadJourneyReports
}));

vi.mock("../../utils/user", () => ({
  ensureUserId: mocks.ensureUserId
}));

const mockLoadJourneyReports = mocks.loadJourneyReports as ReturnType<typeof vi.fn>;
const mockEnsureUserId = mocks.ensureUserId as ReturnType<typeof vi.fn>;

describe("useJourneyReports", () => {
  beforeEach(() => {
    mockLoadJourneyReports.mockReset();
    mockEnsureUserId.mockReturnValue("test-user");
  });

  it("normalizes journey reports and builds conversation lookup map", async () => {
    const payload: JourneyReportsPayload = {
      source: "api",
      daily: [
        {
          reportDate: "2025-02-03",
          title: "今日小结",
          spotlight: "继续练习 4-7-8 呼吸。",
          summary: "晚间焦虑有所下降。",
          moodDelta: 1
        },
        {
          reportDate: "2025-02-02",
          title: "昨日回顾",
          spotlight: "记录两次情绪波动。",
          summary: "识别压力源并尝试写情绪日记。",
          moodDelta: 0
        }
      ],
      weekly: [
        {
          weekStart: "2025-01-27",
          themes: ["睡眠节律"],
          highlights: "坚持睡前放松练习。",
          actionItems: ["继续使用睡前呼吸练习"],
          riskLevel: "low"
        }
      ],
      conversations: [
        {
          sessionId: "session-1",
          startedAt: "2025-02-03T10:00:00Z",
          updatedAt: "2025-02-03T10:05:00Z",
          therapistId: null,
          messages: [
            {
              messageId: "m1",
              role: "user",
              content: "最近晚上的焦虑好多了。",
              createdAt: "2025-02-03T10:00:00Z"
            }
          ]
        },
        {
          sessionId: "session-2",
          startedAt: "2025-02-02T09:30:00Z",
          updatedAt: "2025-02-02T09:45:00Z",
          therapistId: null,
          messages: [
            {
              messageId: "m2",
              role: "assistant",
              content: "我们回顾一下触发点。",
              createdAt: "2025-02-02T09:31:00Z"
            }
          ]
        }
      ]
    };

    mockLoadJourneyReports.mockResolvedValue(payload);

    const { result } = renderHook(() => useJourneyReports("zh-CN"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockLoadJourneyReports).toHaveBeenCalledWith("test-user", "zh-CN");
    expect(result.current.source).toBe("api");
    expect(result.current.error).toBeNull();

    expect(result.current.daily).toHaveLength(2);
    expect(result.current.daily[0]).toMatchObject({
      id: "2025-02-03",
      parsedDate: expect.any(Date)
    });
    expect(result.current.weekly).toHaveLength(1);
    expect(result.current.weekly[0]).toMatchObject({
      id: "2025-01-27",
      parsedWeekStart: expect.any(Date)
    });

    expect(result.current.conversations).toHaveLength(2);
    expect(result.current.conversations[0]).toMatchObject({
      parsedStartedAt: expect.any(Date),
      parsedUpdatedAt: expect.any(Date)
    });

    expect(Array.from(result.current.conversationsByDate.keys())).toEqual(["2025-02-03", "2025-02-02"]);
    expect(result.current.conversationsByDate.get("2025-02-03")).toHaveLength(1);
    expect(result.current.conversationsByDate.get("2025-02-02")).toHaveLength(1);
  });

  it("surfaces errors and clears data when loading fails", async () => {
    const error = new Error("network unavailable");
    mockLoadJourneyReports.mockRejectedValue(error);

    const { result } = renderHook(() => useJourneyReports("en-US"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockLoadJourneyReports).toHaveBeenCalledWith("test-user", "en-US");
    expect(result.current.source).toBe("fallback");
    expect(result.current.error).toBe(error);
    expect(result.current.daily).toEqual([]);
    expect(result.current.weekly).toEqual([]);
    expect(result.current.conversations).toEqual([]);
    expect(result.current.conversationsByDate.size).toBe(0);
  });
});
