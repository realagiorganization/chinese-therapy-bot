import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FALLBACK_UAT_INSIGHTS, loadUATInsights } from "./uat";

describe("loadUATInsights", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("parses summary and backlog data from the API", async () => {
    const summaryPayload = {
      total_sessions: 5,
      distinct_participants: 3,
      average_satisfaction: 4.5,
      average_trust: 4.2,
      sessions_with_blockers: 1,
      issues_by_severity: [
        { severity: "high", count: 1 },
        { severity: "medium", count: 2 }
      ],
      sessions_by_platform: [
        { key: "ios", total: 3, average_satisfaction: 4.7, average_trust: 4.4 }
      ],
      sessions_by_environment: [
        { key: "production", total: 4, average_satisfaction: 4.6, average_trust: 4.3 }
      ]
    };

    const backlogPayload = {
      total: 1,
      items: [
        {
          title: "Voice capture stalls",
          severity: "high",
          occurrences: 2,
          affected_participants: 2,
          latest_session_date: "2025-11-05T10:24:00Z",
          sample_notes: ["Recording halts after 15 seconds."],
          action_items: ["Add retry logic"]
        }
      ]
    };

    const fetchMock = vi.fn(async (url: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      json: async () =>
        url.toString().includes("/summary") ? summaryPayload : backlogPayload
    })) as unknown as typeof fetch;

    vi.stubGlobal("fetch", fetchMock);

    const result = await loadUATInsights({ cohort: "pilot" });

    expect(result.source).toBe("api");
    expect(result.summary.totalSessions).toBe(5);
    expect(result.summary.issuesBySeverity).toHaveLength(2);
    expect(result.backlog.items[0]).toMatchObject({
      title: "Voice capture stalls",
      severity: "high",
      occurrences: 2
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("falls back to seeded data when the API fails", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 503
    })) as unknown as typeof fetch;

    vi.stubGlobal("fetch", fetchMock);

    const result = await loadUATInsights();

    expect(result.source).toBe("fallback");
    expect(result.summary).toEqual(FALLBACK_UAT_INSIGHTS.summary);
    expect(result.backlog).toEqual(FALLBACK_UAT_INSIGHTS.backlog);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
