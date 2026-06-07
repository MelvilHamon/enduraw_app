import { useState } from "react";
import { listDailyMetrics } from "../api/endpoints";
import type { DailyMetricOut } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { LineChart } from "../components/LineChart";
import { Spinner } from "../components/Spinner";
import { Card, PageHeader, PillTabs } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";
import { formatDuration, summarize, type Stats } from "../lib/stats";

const ACCENT = "#F97316";

async function loadHealth(days: number): Promise<DailyMetricOut[]> {
  const rows = await listDailyMetrics(daysAgoISO(days), todayISO());
  // Backend returns newest-first; charts + stats want chronological order.
  return [...rows].sort((a, b) => a.date.localeCompare(b.date));
}

const RANGES: { value: number; label: string }[] = [
  { value: 30, label: "30 j" },
  { value: 90, label: "90 j" },
  { value: 180, label: "180 j" },
];

// Onglet 4 — Santé. Concise watch-derived metrics, each tappable for detail:
// VFC (HRV), score de sommeil, body battery, stress montre.
export function HealthPage() {
  const [days, setDays] = useState(30);
  const { data, error, loading, reload } = useAsync(() => loadHealth(days), [days]);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader
        title="Santé"
        subtitle="Tes données importées de la montre."
        action={<PillTabs value={days} onChange={setDays} options={RANGES} />}
      />

      {loading && <Spinner label="Chargement de tes données…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Metrics rows={data} />}
    </div>
  );
}

function Metrics({ rows }: { rows: DailyMetricOut[] }) {
  const dates = rows.map((r) => r.date);
  const points = (sel: (r: DailyMetricOut) => number | null) =>
    rows.map((r) => ({ date: r.date, value: sel(r) }));

  const sleepMeanDuration = summarize(rows.map((r) => r.sleep_duration_min)).mean;

  return (
    <div className="flex flex-col gap-4">
      <HealthMetric
        title="VFC (HRV)"
        hint="RMSSD nuit par nuit · plus haut = mieux récupéré"
        points={points((r) => r.hrv_rmssd)}
        unit=" ms"
        decimals={0}
      />
      <HealthMetric
        title="Sommeil"
        hint="Score de sommeil · /100"
        points={points((r) => r.sleep_score)}
        unit=" /100"
        decimals={0}
        extra={
          sleepMeanDuration !== null
            ? `Durée moyenne : ${formatDuration(sleepMeanDuration)}`
            : undefined
        }
      />
      <HealthMetric
        title="Body battery"
        hint="Réserve d'énergie estimée · /100"
        points={points((r) => r.body_battery)}
        unit=" /100"
        decimals={0}
      />
      <HealthMetric
        title="Stress (montre)"
        hint="Stress mesuré · plus bas = mieux · /100"
        points={points((r) => r.stress)}
        unit=" /100"
        decimals={0}
      />
      {dates.length === 0 && (
        <p className="text-sm text-stone-500">Aucune donnée montre sur la période.</p>
      )}
    </div>
  );
}

interface HealthMetricProps {
  title: string;
  hint: string;
  points: { date: string; value: number | null }[];
  unit?: string;
  decimals?: number;
  extra?: string;
}

// Tap the card to reveal per-metric detail (mean / min / max / n).
function HealthMetric({ title, hint, points, unit, decimals = 0, extra }: HealthMetricProps) {
  const [open, setOpen] = useState(false);
  const stats = summarize(points.map((p) => p.value));
  const fmt = (v: number | null) => (v === null ? "—" : `${Number(v.toFixed(decimals))}`);

  return (
    <Card className="p-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-baseline justify-between gap-2 px-4 pt-4 text-left"
      >
        <span className="text-sm font-semibold text-stone-300">{title}</span>
        <span className="flex items-center gap-2">
          <span className="text-base font-bold text-stone-50">
            {fmt(stats.latest)}
            {unit && <span className="ml-0.5 text-xs font-normal text-stone-400">{unit}</span>}
          </span>
          <span className="text-stone-500">{open ? "▾" : "▸"}</span>
        </span>
      </button>
      <p className="px-4 pt-0.5 text-xs text-stone-500">{hint}</p>

      <div className="px-4 pb-4 pt-2">
        <LineChart series={[{ name: title, color: ACCENT, points }]} unit={unit} />
      </div>

      {open && (
        <div className="border-t border-ink-600 px-4 py-3">
          <Detail stats={stats} unit={unit} decimals={decimals} />
          {extra && <p className="mt-2 text-xs text-stone-400">{extra}</p>}
        </div>
      )}
    </Card>
  );
}

function Detail({ stats, unit, decimals }: { stats: Stats; unit?: string; decimals: number }) {
  const fmt = (v: number | null) =>
    v === null ? "—" : `${Number(v.toFixed(decimals))}${unit ?? ""}`;
  const items: [string, string][] = [
    ["Moyenne", fmt(stats.mean)],
    ["Min", fmt(stats.min)],
    ["Max", fmt(stats.max)],
    ["Mesures", String(stats.n)],
  ];
  return (
    <div className="grid grid-cols-4 gap-2 text-center">
      {items.map(([label, value]) => (
        <div key={label}>
          <div className="text-sm font-semibold text-stone-100">{value}</div>
          <div className="text-[10px] uppercase tracking-wide text-stone-500">{label}</div>
        </div>
      ))}
    </div>
  );
}
