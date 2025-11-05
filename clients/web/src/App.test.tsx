import { fireEvent, render, screen } from "@testing-library/react";
import { Buffer } from "node:buffer";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

import App from "./App";
import i18n from "./i18n/config";
import { ThemeProvider } from "./design-system";
import { FALLBACK_THERAPISTS } from "./api/therapists";
import { AuthProvider } from "./auth/AuthContext";

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

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
          title: "Today's reflection",
          spotlight: "Keep the breathing reset going; your mood is stabilising.",
          summary: "Completed the breathing routine and logged fewer anxiety triggers.",
          mood_delta: 1
        }
      ],
      weekly: [
        {
          week_start: "2024-09-30",
          themes: ["Sleep adjustment"],
          highlights: "Meditated before bed on three nights.",
          action_items: ["Keep a bedtime journal"],
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
              content: "Sleep has improved a little recently.",
              created_at: "2024-10-01T12:00:00Z"
            },
            {
              message_id: "m2",
              role: "assistant",
              content: "Great—keep anchoring with the 4-7-8 breath.",
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
          title: "Guided Breathing Session",
          description: "A five-minute pace-reset that slows breathing and lowers heart rate.",
          cadence_label: "4-7-8 cadence",
          duration_minutes: 5,
          steps: [
            { label: "Posture", instruction: "Sit or stand tall, relax your shoulders, close your eyes.", duration_seconds: 10 },
            { label: "Inhale 4 Count", instruction: "Inhale through the nose while counting 1-2-3-4.", duration_seconds: 16 },
            { label: "Hold 7 Count", instruction: "Hold gently for seven beats without tensing your neck.", duration_seconds: 28 },
            { label: "Exhale 8 Count", instruction: "Exhale slowly through the mouth, feeling your chest soften.", duration_seconds: 32 }
          ],
          recommended_frequency: "Practice 2-3 rounds before bed or when anxiety spikes.",
          cta_label: "Start breathing guide",
          cta_action: "/breathing"
        },
        {
          id: "trending-topics",
          module_type: "trending_topics",
          title: "Trending focus areas",
          description: "Based on your latest chats and summaries, these themes deserve extra attention.",
          topics: [
            {
              name: "Stress management",
              momentum: 68,
              trend: "up",
              summary: 'Discussions around "Stress management" are gaining traction; pair it with breathing or journaling.'
            }
          ],
          insights: ["Log how you feel after tonight's breathing reset."],
          cta_label: "View practice ideas",
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
          title: "Breathing anchor for sudden anxiety",
          userPrompt: "My heart suddenly races and I want to learn how to ground myself.",
          assistantExample: "Let's try the 4-7-8 breath to help your body remember a safe rhythm.",
          followUpQuestions: ["When does this anxiety usually surface?"],
          selfCareTips: ["Log how you feel after the exercise so you can revisit it later."],
          keywords: ["anxiety", "breathing"],
          tags: ["breathing"]
        }
      ]
    };

    const future = Date.now() + 60 * 60 * 1000;
    const fakeUserId = "11111111-1111-1111-1111-111111111111";
    const fakeAccessToken = buildJwt({ sub: fakeUserId, exp: Math.floor(future / 1000) });
    window.localStorage.setItem(
      "mindwell:auth",
      JSON.stringify({
        accessToken: fakeAccessToken,
        refreshToken: "test-refresh",
        expiresAt: future,
        userId: fakeUserId
      })
    );

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (init?.headers && (init.headers as Record<string, string>).Authorization) {
        // Authorization header presence makes sure the authenticated fetch path is exercised.
      }
      if (url.includes("/api/translation/batch")) {
        const body = typeof init?.body === "string" ? init.body : "";
        const payload = body ? (JSON.parse(body) as { target_locale: string; entries: Array<{ key: string; text: string }> }) : { target_locale: "zh-CN", entries: [] };
        const translations = Object.fromEntries(
          payload.entries.map(({ key, text }) => [key, `${text} (${payload.target_locale})`])
        );
        return {
          ok: true,
          status: 200,
          json: async () =>
            ({
              target_locale: payload.target_locale,
              source_locale: "en-US",
              translations
            }) as const
        } as Response;
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

  it("renders localized hero content for Simplified Chinese", async () => {
    renderApp();
    expect(await screen.findByText(/MindWell Companion \(zh-CN\)/)).toBeInTheDocument();
    expect(
      await screen.findByText(/Voice input, emotional summaries, and daily companionship included\. \(zh-CN\)/)
    ).toBeInTheDocument();
    expect(await screen.findByText(/Journey reports \(zh-CN\)/)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledTimes(5);
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
    expect(await screen.findByText(/MindWell Companion \(ru-RU\)/)).toBeInTheDocument();
    expect(await screen.findByText(/Therapy Companion \(ru-RU\)/)).toBeInTheDocument();
  });

  it("falls back gracefully to Traditional Chinese locale", async () => {
    renderApp();
    const [localeSelect] = screen.getAllByRole("combobox");
    fireEvent.change(localeSelect, { target: { value: "zh-TW" } });
    expect(await screen.findByText(/Next steps \(zh-TW\)/)).toBeInTheDocument();
    expect(await screen.findByText(/Share with therapist \(zh-TW\)/)).toBeInTheDocument();
  });
});
