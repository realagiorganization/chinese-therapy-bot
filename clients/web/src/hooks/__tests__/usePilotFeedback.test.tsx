import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PilotFeedbackSnapshot } from "../../api/types";
import { usePilotFeedback } from "../usePilotFeedback";

const mocks = vi.hoisted(() => ({
  loadPilotFeedbackSnapshot: vi.fn()
}));

vi.mock("../../api/feedback", async () => {
  const actual = await vi.importActual<typeof import("../../api/feedback")>(
    "../../api/feedback"
  );
  return {
    ...actual,
    loadPilotFeedbackSnapshot: mocks.loadPilotFeedbackSnapshot
  };
});

const mockLoadPilotFeedbackSnapshot = mocks.loadPilotFeedbackSnapshot as ReturnType<typeof vi.fn>;

const SAMPLE_SNAPSHOT: PilotFeedbackSnapshot = {
  source: "api",
  backlog: [
    {
      label: "语音播报稳定性",
      tag: "voice",
      scenario: "mobile-chat",
      cohorts: ["pilot-2025w4"],
      frequency: 3,
      participantCount: 2,
      followUpCount: 1,
      averageSentiment: 3.6,
      averageTrust: 3.2,
      averageUsability: 2.8,
      priorityScore: 0.74,
      representativeSeverity: "medium",
      lastSubmittedAt: "2025-01-21T09:00:00Z",
      highlights: ["音色自然，播放平稳。"],
      blockers: ["部分设备暂停后无法恢复。"]
    }
  ],
  participants: [
    {
      id: "participant-1",
      cohort: "pilot-2025w4",
      fullName: "Lin An",
      preferredName: "安安",
      displayName: "安安",
      status: "active",
      channel: "mobile",
      tags: ["voice"],
      requiresFollowUp: true,
      lastContactAt: "2025-01-21T08:30:00Z",
      followUpNotes: "等待语音补丁发布后回访。",
      updatedAt: "2025-01-21T08:40:00Z"
    }
  ],
  recentFeedback: [
    {
      id: "feedback-1",
      cohort: "pilot-2025w4",
      scenario: "mobile-chat",
      participantAlias: "安安",
      channel: "mobile",
      highlights: "语音播放帮助我快速平静。",
      blockers: "偶尔停顿，需要重新进入。",
      tags: ["voice"],
      sentimentScore: 4,
      trustScore: 3,
      usabilityScore: 2,
      followUpNeeded: true,
      severity: "high",
      submittedAt: "2025-01-21T08:45:00Z"
    }
  ]
};

describe("usePilotFeedback", () => {
  beforeEach(() => {
    mockLoadPilotFeedbackSnapshot.mockReset();
    mockLoadPilotFeedbackSnapshot.mockResolvedValue(SAMPLE_SNAPSHOT);
  });

  it("returns pilot feedback snapshot data and metadata", async () => {
    const { result } = renderHook(() => usePilotFeedback({ cohort: "pilot-2025w4", limit: 4 }));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockLoadPilotFeedbackSnapshot).toHaveBeenCalledWith({
      cohort: "pilot-2025w4",
      limit: 4
    });
    expect(result.current.source).toBe("api");
    expect(result.current.backlog).toEqual(SAMPLE_SNAPSHOT.backlog);
    expect(result.current.participants).toEqual(SAMPLE_SNAPSHOT.participants);
    expect(result.current.recentFeedback).toEqual(SAMPLE_SNAPSHOT.recentFeedback);
    expect(result.current.error).toBeNull();
  });

  it("exposes fallback state when live data is unavailable", async () => {
    mockLoadPilotFeedbackSnapshot.mockResolvedValueOnce({
      ...SAMPLE_SNAPSHOT,
      source: "fallback"
    });

    const { result } = renderHook(() => usePilotFeedback());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.source).toBe("fallback");
    expect(result.current.error?.message).toBe("pilot-feedback-fallback");
  });

  it("refreshes snapshot on demand", async () => {
    const { result } = renderHook(() => usePilotFeedback());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    mockLoadPilotFeedbackSnapshot.mockResolvedValueOnce(SAMPLE_SNAPSHOT);

    await act(async () => {
      await result.current.refresh();
    });

    expect(mockLoadPilotFeedbackSnapshot).toHaveBeenCalledTimes(2);
  });
});
