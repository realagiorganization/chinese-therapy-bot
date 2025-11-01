import { fireEvent, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

import App from "./App";
import i18n from "./i18n/config";
import { ThemeProvider } from "./design-system";
import { FALLBACK_THERAPISTS } from "./api/therapists";

function renderApp() {
  return render(
    <I18nextProvider i18n={i18n}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </I18nextProvider>
  );
}

describe("App", () => {
  beforeEach(() => {
    const therapistResponse = {
      items: FALLBACK_THERAPISTS.map((therapist) => ({
        therapist_id: therapist.id,
        name: therapist.name,
        title: therapist.title,
        specialties: therapist.specialties,
        languages: therapist.languages,
        price_per_session: therapist.price,
        currency: therapist.currency ?? "CNY",
        is_recommended: therapist.recommended,
        availability: therapist.availability
      }))
    };

    const journeyResponse = {
      daily: [
        {
          report_date: "2024-10-01",
          title: "今日回顾",
          spotlight: "继续呼吸放松练习。",
          summary: "完成了放松训练，焦虑指数下降。",
          mood_delta: 1
        }
      ],
      weekly: [
        {
          week_start: "2024-09-30",
          themes: ["睡眠调整"],
          highlights: "坚持睡前冥想三晚。",
          action_items: ["继续记录睡前情绪"],
          risk_level: "low"
        }
      ],
      conversations: [
        {
          session_id: "abc",
          started_at: "2024-10-01T12:00:00Z",
          updated_at: "2024-10-01T12:10:00Z",
          therapist_id: null,
          messages: [
            {
              message_id: "m1",
              role: "user",
              content: "最近睡眠改善了一些。",
              created_at: "2024-10-01T12:00:00Z"
            },
            {
              message_id: "m2",
              role: "assistant",
              content: "很好，继续保持呼吸练习。",
              created_at: "2024-10-01T12:01:00Z"
            }
          ]
        }
      ]
    };

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/therapists")) {
        return {
          ok: true,
          status: 200,
          json: async () => therapistResponse
        } as Response;
      }
      if (url.includes("/api/reports/")) {
        return {
          ok: true,
          status: 200,
          json: async () => journeyResponse
        } as Response;
      }
      return {
        ok: false,
        status: 404,
        json: async () => ({})
      } as Response;
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Mandarin-first hero headline", async () => {
    renderApp();
    expect(await screen.findByText(/MindWell 心理陪伴/)).toBeInTheDocument();
    expect(await screen.findByText(/支持语音输入/)).toBeInTheDocument();
    expect(await screen.findByText(/疗愈陪伴对话/)).toBeInTheDocument();
    expect(await screen.findByText(/旅程报告/)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  it("switches to English locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "en-US" } });
    expect(await screen.findByText(/MindWell Companion/)).toBeInTheDocument();
    expect(await screen.findByText(/Therapy Companion/)).toBeInTheDocument();
  });

  it("falls back gracefully to Traditional Chinese locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "zh-TW" } });
    expect(await screen.findByText(/建議下一步/)).toBeInTheDocument();
    expect(await screen.findByText(/分享給治療師/)).toBeInTheDocument();
  });
});
