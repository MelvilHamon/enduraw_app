import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { CheckinOut, DailyRead } from "../api/types";

// Mock the API layer so the screens render without network.
vi.mock("../api/endpoints", () => ({
  getToday: vi.fn(),
  getCheckinToday: vi.fn(),
  upsertCheckin: vi.fn(),
}));

import { getCheckinToday, getToday } from "../api/endpoints";
import { TodayPage } from "../pages/TodayPage";
import { RoutinePage } from "../pages/RoutinePage";

const READ: DailyRead = {
  date: "2026-06-05",
  composite_score: 0.42,
  engine_state: null,
  readiness: {
    reco: "lighten",
    explanation: "Ease up a bit today — your form and feel disagree.",
    top_2: [
      {
        key: "divergence_subj_obj",
        triggered: true,
        severity: 0.6,
        value: 1.2,
        reference: 0,
        delta: 1.2,
        direction: "subj_optimistic",
        explanation: "You feel better than your data suggests.",
        evidence: ["z_subj=1.0", "z_engine=-0.2"],
      },
    ],
  },
  signals: [
    {
      key: "divergence_subj_obj",
      triggered: true,
      severity: 0.6,
      value: 1.2,
      reference: 0,
      delta: 1.2,
      direction: "subj_optimistic",
      explanation: "You feel better than your data suggests.",
      evidence: ["z_subj=1.0", "z_engine=-0.2"],
    },
  ],
};

describe("TodayPage", () => {
  it("renders the reco and the divergence headline", async () => {
    vi.mocked(getToday).mockResolvedValue(READ);
    vi.mocked(getCheckinToday).mockResolvedValue({} as never);

    render(
      <MemoryRouter>
        <TodayPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("Tu te sens mieux que ce que dit ton corps."),
    ).toBeInTheDocument();
    expect(screen.getByText("Allège ta séance")).toBeInTheDocument();
    expect(screen.getByText(READ.readiness.explanation)).toBeInTheDocument();
  });
});

const CHECKIN: CheckinOut = {
  id: "1",
  date: "2026-06-06",
  form_vs_normal: 1,
  motivation: 2,
  fatigue: 3,
  stress: -1,
  reported_at: "2026-06-06T07:30:00Z",
  created_at: "2026-06-06T07:30:00Z",
  updated_at: "2026-06-06T07:30:00Z",
};

describe("RoutinePage", () => {
  it("shows the recap when the routine is already done today", async () => {
    vi.mocked(getCheckinToday).mockResolvedValue(CHECKIN);

    render(
      <MemoryRouter>
        <RoutinePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Routine faite ✓")).toBeInTheDocument();
    expect(screen.getByText("Refaire la routine")).toBeInTheDocument();
  });
});
