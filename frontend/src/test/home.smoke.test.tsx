import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { CheckinOut, MiniTestOut } from "../api/types";

vi.mock("../api/endpoints", () => ({
  listCheckins: vi.fn(),
  listMiniTests: vi.fn(),
}));

import { listCheckins, listMiniTests } from "../api/endpoints";
import { HomePage } from "../pages/HomePage";

const CHECKINS: CheckinOut[] = [
  {
    id: "1",
    date: "2026-06-05",
    form_vs_normal: 1,
    motivation: 1,
    fatigue: 2,
    stress: -1,
    reported_at: "2026-06-05T18:00:00Z",
    created_at: "2026-06-05T18:00:00Z",
    updated_at: "2026-06-05T18:00:00Z",
  },
  {
    id: "2",
    date: "2026-06-06",
    form_vs_normal: 2,
    motivation: 2,
    fatigue: 1,
    stress: 0,
    reported_at: "2026-06-06T18:00:00Z",
    created_at: "2026-06-06T18:00:00Z",
    updated_at: "2026-06-06T18:00:00Z",
  },
];

const REACTION: MiniTestOut[] = [
  {
    id: "r1",
    date: "2026-06-05",
    reported_at: "2026-06-05T18:00:00Z",
    type: "reaction",
    data: { mean_rt_ms: 250, sd_rt_ms: 30, n_taps: 30 },
    created_at: "2026-06-05T18:00:00Z",
    updated_at: "2026-06-05T18:00:00Z",
  },
];

describe("HomePage", () => {
  it("renders the input curves in spec order", async () => {
    vi.mocked(listCheckins).mockResolvedValue(CHECKINS);
    vi.mocked(listMiniTests).mockImplementation((_from, _to, type) =>
      Promise.resolve(type === "reaction" ? REACTION : []),
    );

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Forme")).toBeInTheDocument();
    expect(screen.getByText("Fatigue")).toBeInTheDocument();
    expect(screen.getByText("Motivation")).toBeInTheDocument();
    expect(screen.getByText("Stress")).toBeInTheDocument();
    expect(screen.getByText("Temps de réaction")).toBeInTheDocument();
    expect(screen.getByText("Saut")).toBeInTheDocument();
  });
});
