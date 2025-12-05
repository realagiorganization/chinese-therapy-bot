import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FALLBACK_THERAPISTS, loadTherapists } from "./therapists";

describe("loadTherapists", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns API results when fetch succeeds", async () => {
    const payload = {
      items: [
        {
          therapist_id: "t-1",
          name: "Alex Zhang",
          title: "Licensed counseling psychologist",
          specialties: ["Anxiety regulation"],
          languages: ["en-US"],
          price_per_session: 520,
          currency: "CNY",
          is_recommended: true,
          availability: ["Friday 20:00"],
          recommendation_reason: "Focuses on anxiety regulation themes."
        }
      ]
    };

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => payload
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadTherapists();

    expect(result.source).toBe("api");
    expect(result.therapists).toHaveLength(1);
    expect(result.therapists[0]).toMatchObject({
      id: "t-1",
      name: "Alex Zhang",
      specialties: ["Anxiety regulation"],
      languages: ["en-US"],
      recommended: true,
      price: 520,
      recommendationReason: "Focuses on anxiety regulation themes."
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("falls back to seed data when fetch fails", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 503
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadTherapists();

    expect(result.source).toBe("fallback");
    expect(result.therapists).toEqual(FALLBACK_THERAPISTS);
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
