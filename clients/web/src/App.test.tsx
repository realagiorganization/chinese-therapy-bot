import { render, screen } from "@testing-library/react";
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
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
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
      })
    })) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Mandarin-first hero headline", () => {
    renderApp();
    expect(screen.getByText(/MindWell 心理陪伴/)).toBeInTheDocument();
    expect(screen.getByText(/支持语音输入/)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("switches to English locale", async () => {
    renderApp();
    const select = screen.getByRole("combobox");
    select.value = "en";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(await screen.findByText(/MindWell Companion/)).toBeInTheDocument();
  });
});
