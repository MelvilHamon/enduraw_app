// Generic metric card: a compact summary visual by default; tap to expand a
// detail panel with the soft gradient AreaChart, a period switcher, and the
// period-average + 7-day-average reference lines. Reused across Accueil, Charge
// and Santé so every metric behaves the same way.

import { useState, type ReactNode } from "react";
import { daysAgoISO } from "../lib/date";
import { meanLastN, summarize, type DatedPoint } from "../lib/stats";
import { AreaChart } from "./charts/AreaChart";
import { ChevronIcon } from "./icons";
import { Card } from "./ui";
import { PillTabs } from "./ui";

interface MetricCardProps {
  title: string;
  hint?: string;
  color: string;
  // Full chronological series; the card slices it for the detail period.
  points: DatedPoint[];
  today: string; // todayISO
  summary: ReactNode; // collapsed visual (CompareTriple, etc.)
  unit?: string;
  decimals?: number;
}

const RANGES: { value: number; label: string }[] = [
  { value: 7, label: "7 j" },
  { value: 30, label: "30 j" },
];

export function MetricCard({
  title,
  hint,
  color,
  points,
  today,
  summary,
  unit,
  decimals = 0,
}: MetricCardProps) {
  const [open, setOpen] = useState(false);
  const [days, setDays] = useState(30);

  const from = daysAgoISO(days);
  const windowed = points.filter((p) => p.date >= from);
  const periodMean = summarize(windowed.map((p) => p.value)).mean;
  const mean7 = meanLastN(points, 7, today);

  return (
    <Card className="p-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-4 pt-4 text-left"
      >
        <span className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
          <span className="text-sm font-semibold text-stone-100">{title}</span>
        </span>
        <ChevronIcon open={open} className="text-stone-500" />
      </button>
      {hint && <p className="px-4 pt-1 text-xs text-stone-400">{hint}</p>}

      <div className="px-4 pb-4 pt-3">{summary}</div>

      {open && (
        <div className="border-t border-ink-600 px-4 py-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-400">Historique</span>
            <PillTabs value={days} onChange={setDays} options={RANGES} />
          </div>
          <AreaChart
            points={windowed}
            color={color}
            unit={unit}
            decimals={decimals}
            mean={periodMean}
            mean7={mean7}
          />
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-stone-400">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-0 w-4 border-t border-dashed border-stone-500" />
              Moyenne période
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-0 w-4 border-t border-dashed" style={{ borderColor: color }} />
              Moyenne 7 j
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
