// A single-metric card: title + latest value headline + scaled line chart.
// Reused across the Accueil / Charge / Santé tabs so every curve looks the same.

import { LineChart } from "./LineChart";
import { Card } from "./ui";

export interface MetricPoint {
  date: string;
  value: number | null;
}

// Brand accent — the design brief keeps every curve in orange.
const ACCENT = "#F97316";

interface MetricChartProps {
  title: string;
  points: MetricPoint[];
  hint?: string;
  unit?: string;
  // Decimals for the headline + axis labels (default 0).
  decimals?: number;
  // Draw a dashed y=0 reference (e.g. signed -2..+2 scales).
  zeroLine?: boolean;
  color?: string;
  height?: number;
}

function latestPoint(points: MetricPoint[]): MetricPoint | null {
  let best: MetricPoint | null = null;
  for (const p of points) {
    if (p.value === null) continue;
    if (best === null || p.date >= best.date) best = p;
  }
  return best;
}

export function MetricChart({
  title,
  points,
  hint,
  unit,
  decimals = 0,
  zeroLine = false,
  color = ACCENT,
  height,
}: MetricChartProps) {
  const latest = latestPoint(points);
  const fmt = (v: number) => `${Number(v.toFixed(decimals))}`;

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-300">{title}</h2>
        {latest && (
          <span className="text-base font-bold text-stone-50">
            {fmt(latest.value as number)}
            {unit && <span className="ml-0.5 text-xs font-normal text-stone-400">{unit}</span>}
          </span>
        )}
      </div>
      {hint && <p className="mt-0.5 text-xs text-stone-500">{hint}</p>}
      <div className="mt-2">
        <LineChart
          series={[{ name: title, color, points }]}
          zeroLine={zeroLine}
          unit={unit}
          formatValue={decimals > 0 ? fmt : undefined}
          height={height}
        />
      </div>
    </Card>
  );
}
