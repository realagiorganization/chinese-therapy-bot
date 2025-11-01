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
  locale: "zh-CN",
  title: "緩解焦慮的呼吸練習",
  userPrompt: "最近心跳總是突然加快，想學緩和情緒的方法。",
  assistantExample: "讓我們先用 4-7-8 呼吸慢慢穩定身體的反應。",
  followUpQuestions: ["什麼時候最容易感到焦慮？"],
  selfCareTips: ["每天至少練習兩次深呼吸輪次。"],
  keywords: ["焦慮", "呼吸"],
  tags: ["breathing"]
};

describe("useChatTemplates", () => {
  beforeEach(() => {
    mockLoadChatTemplates.mockReset();
  });

  it("fetches templates and exposes available topics", async () => {
    mockLoadChatTemplates.mockResolvedValue({
      locale: "zh-CN",
      topics: ["anxiety", "sleep"],
      templates: [BASE_TEMPLATE]
    });

    const { result } = renderHook(() => useChatTemplates("zh-CN"));

    await waitFor(() => expect(result.current.status).toBe("success"));

    expect(result.current.templates).toHaveLength(1);
    expect(result.current.templates[0].id).toBe("anxiety_grounding");
    expect(result.current.topics).toEqual(["anxiety", "sleep"]);

    const firstCall = mockLoadChatTemplates.mock.calls[0][0];
    expect(firstCall.locale).toBe("zh-CN");
    expect(firstCall.topic).toBeUndefined();
  });

  it("refetches when the selected topic changes", async () => {
    mockLoadChatTemplates
      .mockResolvedValueOnce({
        locale: "zh-CN",
        topics: ["anxiety", "sleep"],
        templates: [BASE_TEMPLATE]
      })
      .mockResolvedValueOnce({
        locale: "zh-CN",
        topics: ["anxiety", "sleep"],
        templates: [
          {
            ...BASE_TEMPLATE,
            id: "sleep_routine",
            topic: "sleep",
            title: "睡前儀式",
            userPrompt: "最近都很難入睡，想要一個放鬆流程。",
            keywords: ["睡眠"]
          }
        ]
      });

    const { result } = renderHook(() => useChatTemplates("zh-CN"));
    await waitFor(() => expect(result.current.status).toBe("success"));

    act(() => {
      result.current.setSelectedTopic("sleep");
    });

    await waitFor(() => expect(mockLoadChatTemplates).toHaveBeenCalledTimes(2));

    const secondCall = mockLoadChatTemplates.mock.calls[1][0];
    expect(secondCall.locale).toBe("zh-CN");
    expect(secondCall.topic).toBe("sleep");
  });
});
