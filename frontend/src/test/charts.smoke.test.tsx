import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { DailyMetricOut, Timeseries } from "../api/types";

vi.mock("../api/endpoints", () => ({
  getTimeseries: vi.fn(),
  listDailyMetrics: vi.fn(),
}));

import { getTimeseries, listDailyMetrics } from "../api/endpoints";
import { CompareTriple } from "../components/charts/CompareTriple";
import { ArcGauge, RingGauge, SegmentedGauge } from "../components/charts/Gauge";
import { PhaseBar } from "../components/charts/PhaseBar";
import { Thermometer } from "../components/charts/Thermometer";
import { WeeklyBars } from "../components/charts/WeeklyBars";
import { AreaChart } from "../components/charts/AreaChart";
import { VO2_SEGMENTS, acwrColor } from "../lib/palette";
import { HealthPage } from "../pages/HealthPage";
import { LoadPage } from "../pages/LoadPage";

function metric(date: string, over: Partial<DailyMetricOut> = {}): DailyMetricOut {
  return {
    id: date,
    date,
    sleep_score: 78,
    sleep_duration_min: 432,
    sleep_onset: null,
    sleep_wake: null,
    hrv_rmssd: 62,
    hrv_status: "normal",
    rhr: 48,
    stress: 31,
    body_battery: 74,
    resp_rate: 14,
    training_readiness: 69,
    vo2max: 58.1,
    source: "garmin_faked",
    created_at: `${date}T00:00:00Z`,
    updated_at: `${date}T00:00:00Z`,
    ...over,
  };
}

const DAILY: DailyMetricOut[] = [
  metric("2026-06-01", { vo2max: 57.8, body_battery: 60, sleep_score: 70, hrv_rmssd: 55 }),
  metric("2026-06-04", { vo2max: 58.0, body_battery: 68 }),
  metric("2026-06-06", { vo2max: 58.3 }),
];

const TS: Timeseries = {
  date_from: "2026-06-01",
  date_to: "2026-06-06",
  series: {
    form: [
      { date: "2026-06-01", value: -4.2 },
      { date: "2026-06-04", value: 2.1 },
      { date: "2026-06-06", value: 6.5 },
    ],
    acwr: [
      { date: "2026-06-01", value: 0.9 },
      { date: "2026-06-04", value: 1.1 },
      { date: "2026-06-06", value: 1.4 },
    ],
  },
  form_vs_normal: [],
  divergence: [],
};

describe("LoadPage", () => {
  it("renders VO2 gauge, ACWR bars and the Banister form card", async () => {
    vi.mocked(getTimeseries).mockResolvedValue(TS);
    vi.mocked(listDailyMetrics).mockResolvedValue(DAILY);

    render(
      <MemoryRouter>
        <LoadPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/VO2 max/)).toBeInTheDocument();
    expect(screen.getByText("ACWR par semaine")).toBeInTheDocument();
    expect(screen.getByText("Forme (calculée)")).toBeInTheDocument();
  });
});

describe("HealthPage", () => {
  it("renders the four watch metrics with their visuals", async () => {
    vi.mocked(listDailyMetrics).mockResolvedValue(DAILY);

    render(
      <MemoryRouter>
        <HealthPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("VFC (HRV)")).toBeInTheDocument();
    expect(screen.getByText("Sommeil")).toBeInTheDocument();
    expect(screen.getByText("Body battery")).toBeInTheDocument();
    expect(screen.getByText("Stress (montre)")).toBeInTheDocument();
  });
});

describe("chart primitives — edge cases", () => {
  it("render without throwing on empty / null data", () => {
    const { container } = render(
      <div>
        <CompareTriple today={null} yesterday={null} mean7={null} color="#F97316" />
        <CompareTriple today={250} yesterday={260} mean7={255} color="#38BDF8" unit=" ms" mode="deviation" betterLower />
        <AreaChart points={[]} color="#F97316" />
        <AreaChart
          points={[
            { date: "2026-06-01", value: 1 },
            { date: "2026-06-02", value: null },
            { date: "2026-06-03", value: 3 },
          ]}
          color="#F97316"
          mean={2}
          mean7={2.5}
        />
        <SegmentedGauge value={null} min={30} max={70} segments={VO2_SEGMENTS} centerLabel="—" />
        <SegmentedGauge value={58.1} min={30} max={70} segments={VO2_SEGMENTS} centerLabel="58.1" delta={0.3} />
        <ArcGauge value={null} />
        <ArcGauge value={74} />
        <RingGauge value={78} />
        <RingGauge value={null} />
        <PhaseBar value={null} min={0} max={100} />
        <PhaseBar value={62} min={40} max={90} unit=" ms" />
        <Thermometer value={null} />
        <Thermometer value={31} />
        <WeeklyBars bars={[]} />
        <WeeklyBars bars={[{ label: "S-1", value: 1.1, color: acwrColor(1.1) }, { label: "S0", value: null, color: "#333" }]} band={{ from: 0.8, to: 1.3 }} />
      </div>,
    );
    // Sanity: SVGs mounted.
    expect(container.querySelectorAll("svg").length).toBeGreaterThan(5);
  });
});
