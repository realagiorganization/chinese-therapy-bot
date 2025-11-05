import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChatTemplate } from "../../api/types";
import { useChatTemplates } from "../useChatTemplates";

const mocks = vi.hoisted(() => ({
  loadChatTemplates: vi.fn()
}));

vi.mock("../../api/templates", () => ({
  loadChatTemplates: mocks.loadChatTemplates
}));

const mockLoadChatTemplates = mocks.loadChatTemplates as ReturnType<typeof vi.fn>;

const BASE_TEMPLATE: ChatTemplate = {
  id: "anxiety_grounding",
  topic: "anxiety",
  locale: "en-US",
  title: "Breathing anchor for anxious spikes",
  userPrompt: "My heart suddenly races and I need a way to steady my emotions.",
  assistantExample: "Let's take a 4-7-8 breath to help your body remember a calmer rhythm.",
  followUpQuestions: ["When do you notice this anxiety showing up most often?"],
  selfCareTips: ["Practice two full breathing rounds twice a day."],
  keywords: ["anxiety", "breathing"],
  tags: ["breathing"]
};

describe("useChatTemplates", () => {
  beforeEach(() => {
    mockLoadChatTemplates.mockReset();
  });

  it("fetches templates and exposes available topics", async () => {
    mockLoadChatTemplates.mockResolvedValue({
      locale: "en-US",
      topics: ["anxiety", "sleep"],
      templates: [BASE_TEMPLATE]
    });

    const { result } = renderHook(() => useChatTemplates("en-US"));

    await waitFor(() => expect(result.current.status).toBe("success"));

    expect(result.current.templates).toHaveLength(1);
    expect(result.current.templates[0].id).toBe("anxiety_grounding");
    expect(result.current.topics).toEqual(["anxiety", "sleep"]);
    const firstCall = mockLoadChatTemplates.mock.calls[0][0];
    expect(firstCall.locale).toBe("en-US");
    expect(firstCall.topic).toBeUndefined();
  });

  it("refetches when the selected topic changes", async () => {
    mockLoadChatTemplates
      .mockResolvedValueOnce({
        locale: "en-US",
        topics: ["anxiety", "sleep"],
        templates: [BASE_TEMPLATE]
      })
      .mockResolvedValueOnce({
        locale: "en-US",
        topics: ["anxiety", "sleep"],
        templates: [
          {
            ...BASE_TEMPLATE,
            id: "sleep_routine",
            topic: "sleep",
            title: "Wind-down ritual builder",
            userPrompt: "I've struggled to fall asleep lately and need a calming routine.",
            keywords: ["sleep"]
          }
        ]
      });

    const { result } = renderHook(() => useChatTemplates("en-US"));
    await waitFor(() => expect(result.current.status).toBe("success"));

    act(() => {
      result.current.setSelectedTopic("sleep");
    });

    await waitFor(() => expect(mockLoadChatTemplates).toHaveBeenCalledTimes(2));

    const secondCall = mockLoadChatTemplates.mock.calls[1][0];
    expect(secondCall.locale).toBe("en-US");
    expect(secondCall.topic).toBe("sleep");
  });
});
