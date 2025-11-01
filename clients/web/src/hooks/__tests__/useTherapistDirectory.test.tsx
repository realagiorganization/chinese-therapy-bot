import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TherapistSummary } from "../../api/types";
import { useTherapistDirectory } from "../useTherapistDirectory";

const mocks = vi.hoisted(() => ({
  loadTherapists: vi.fn()
}));

vi.mock("../../api/therapists", () => ({
  loadTherapists: mocks.loadTherapists
}));

const mockLoadTherapists = mocks.loadTherapists as ReturnType<typeof vi.fn>;

const SAMPLE_THERAPISTS: TherapistSummary[] = [
  {
    id: "alpha",
    name: "顾向晨",
    title: "认知行为治疗师",
    specialties: ["CBT", "Mindfulness"],
    languages: ["zh-CN"],
    price: 460,
    recommended: true,
    availability: ["周三 20:00"]
  },
  {
    id: "bravo",
    name: "Morgan Li",
    title: "家庭治疗顾问",
    specialties: ["Family Therapy"],
    languages: ["en-US", "zh-CN"],
    price: 620,
    recommended: false,
    availability: ["周五 19:30"]
  }
];

describe("useTherapistDirectory", () => {
  beforeEach(() => {
    mockLoadTherapists.mockReset();
    mockLoadTherapists.mockResolvedValue({
      therapists: SAMPLE_THERAPISTS,
      source: "api"
    });
  });

  it("derives unique specialties and languages from the therapist pool", async () => {
    const { result } = renderHook(() => useTherapistDirectory());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.source).toBe("api");
    expect(result.current.specialties).toEqual(["CBT", "Family Therapy", "Mindfulness"]);
    expect(result.current.languages).toEqual(["en-US", "zh-CN"]);
    expect(result.current.minPrice).toBe(460);
    expect(result.current.maxPrice).toBe(620);
    expect(result.current.filtered.map((item) => item.id)).toEqual(["alpha", "bravo"]);
  });

  it("applies filters and can reset to the initial dataset", async () => {
    const { result } = renderHook(() => useTherapistDirectory());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setFilters(() => ({
        specialty: undefined,
        language: undefined,
        recommendedOnly: true,
        minPrice: undefined,
        maxPrice: undefined
      }));
    });

    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].id).toBe("alpha");

    act(() => {
      result.current.setFilters((prev) => ({
        ...prev,
        specialty: "Family Therapy"
      }));
    });

    expect(result.current.filtered).toHaveLength(0);

    act(() => {
      result.current.setFilters(() => ({
        specialty: undefined,
        language: undefined,
        recommendedOnly: false,
        minPrice: 600,
        maxPrice: undefined
      }));
    });

    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].id).toBe("bravo");

    act(() => {
      result.current.setFilters((prev) => ({
        ...prev,
        minPrice: undefined
      }));
    });

    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.filtered.map((item) => item.id)).toEqual(["alpha", "bravo"]);
  });
});
