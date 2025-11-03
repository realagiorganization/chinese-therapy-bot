import { fireEvent, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

import App from "./App";
import i18n from "./i18n/config";
import { ThemeProvider } from "./design-system";
import { FALLBACK_THERAPISTS } from "./api/therapists";
import { AuthProvider } from "./auth/AuthContext";

function renderApp() {
  return render(
    <I18nextProvider i18n={i18n}>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
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

    const exploreResponse = {
      locale: "zh-CN",
      evaluated_flags: {
        explore_breathing: true,
        explore_psychoeducation: true,
        explore_trending: true
      },
      modules: [
        {
          id: "breathing-reset",
          module_type: "breathing_exercise",
          title: "今日呼吸练习",
          description: "约 5 分钟的呼吸节奏练习，帮助稳定心率。",
          cadence_label: "4-7-8",
          duration_minutes: 5,
          steps: [
            { label: "吸气", instruction: "缓慢吸气 4 拍", duration_seconds: 16 },
            { label: "屏息", instruction: "屏息 7 拍，放松肩颈", duration_seconds: 28 },
            { label: "呼气", instruction: "缓慢呼气 8 拍", duration_seconds: 32 }
          ],
          recommended_frequency: "睡前或焦虑升高时练习 2-3 轮。",
          cta_label: "开始练习",
          cta_action: "/breathing"
        },
        {
          id: "trending-topics",
          module_type: "trending_topics",
          title: "当前关注焦点",
          description: "根据近期摘要推荐的主题。",
          topics: [
            { name: "压力管理", momentum: 68, trend: "up", summary: "继续保持呼吸练习。" }
          ],
          insights: ["晚间做一次身体扫描，记录放松后的感受。"],
          cta_label: "查看建议",
          cta_action: "/trends"
        }
      ]
    };

    const templatesResponse = {
      locale: "zh-CN",
      topics: ["anxiety", "sleep"],
      templates: [
        {
          id: "anxiety_grounding",
          topic: "anxiety",
          locale: "zh-CN",
          title: "突发焦虑的呼吸锚定",
          userPrompt: "最近心跳突然加快，想学一些帮助自己稳定下来的方法。",
          assistantExample: "让我们先试试 4-7-8 呼吸法，慢慢让身体恢复到安全的节奏。",
          followUpQuestions: ["这种焦虑通常发生在什么情境或时间点？"],
          selfCareTips: ["把练习后的感受记录下来，下次焦虑时可以复习。"],
          keywords: ["焦虑", "呼吸"],
          tags: ["breathing"]
        }
      ]
    };

    const future = Date.now() + 60 * 60 * 1000;
    window.localStorage.setItem(
      "mindwell:auth",
      JSON.stringify({ accessToken: "test-access", refreshToken: "test-refresh", expiresAt: future })
    );

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (init?.headers && (init.headers as Record<string, string>).Authorization) {
        // Authorization header presence makes sure the authenticated fetch path is exercised.
      }
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
      if (url.includes("/api/explore/modules")) {
        return {
          ok: true,
          status: 200,
          json: async () => exploreResponse
        } as Response;
      }
      if (url.includes("/api/chat/templates")) {
        return {
          ok: true,
          status: 200,
          json: async () => templatesResponse
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
    window.localStorage.clear();
  });

  it("renders Mandarin-first hero headline", async () => {
    renderApp();
    expect(await screen.findByText(/MindWell 心理陪伴/)).toBeInTheDocument();
    expect(await screen.findByText(/支持语音输入/)).toBeInTheDocument();
    expect(await screen.findByText(/疗愈陪伴对话/)).toBeInTheDocument();
    expect(await screen.findByText(/旅程报告/)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledTimes(4);
  });

  it("switches to English locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "en-US" } });
    expect(await screen.findByText(/MindWell Companion/)).toBeInTheDocument();
    expect(await screen.findByText(/Therapy Companion/)).toBeInTheDocument();
  });

  it("lists Russian locale option", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    const options = Array.from(localeSelect.querySelectorAll("option")).map((option) => option.value);
    expect(options).toContain("ru-RU");
  });

  it("switches to Russian locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "ru-RU" } });
    expect(await screen.findByText(/MindWell Помощник/)).toBeInTheDocument();
    expect(await screen.findByText(/Диалог с терапевтом/)).toBeInTheDocument();
  });

  it("falls back gracefully to Traditional Chinese locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "zh-TW" } });
    expect(await screen.findByText(/建議下一步/)).toBeInTheDocument();
    expect(await screen.findByText(/分享給治療師/)).toBeInTheDocument();
  });
});
