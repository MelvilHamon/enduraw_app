import { listDailyMetrics } from "../api/endpoints";
import type { DailyMetricOut } from "../api/types";
import { ArcGauge, RingGauge } from "../components/charts/Gauge";
import { PhaseBar } from "../components/charts/PhaseBar";
import { Thermometer } from "../components/charts/Thermometer";
import { ErrorBanner } from "../components/ErrorBanner";
import { NoDataIcon } from "../components/icons";
import { MetricCard } from "../components/MetricCard";
import { CardSkeleton, HeroSkeleton } from "../components/Skeleton";
import { Card, CardTitle, EmptyState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";
import { METRIC_COLOR, PHASE_COLORS } from "../lib/palette";
import { formatDuration, meanLastN, summarize, type DatedPoint } from "../lib/stats";

const WINDOW_DAYS = 180;

async function loadHealth(): Promise<DailyMetricOut[]> {
  const rows = await listDailyMetrics(daysAgoISO(WINDOW_DAYS), todayISO());
  return [...rows].sort((a, b) => a.date.localeCompare(b.date));
}

// Onglet 4 — Santé. Each watch metric gets its own visual (gauge / phase bar /
// thermometer); tap a card to reveal the history curve with average references.
export function HealthPage() {
  const { data, error, loading, reload } = useAsync(loadHealth, []);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Santé" subtitle="Tes données importées de la montre." />

      {loading && (
        <div className="flex flex-col gap-4">
          <HeroSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Metrics rows={data} />}
    </div>
  );
}

function Metrics({ rows }: { rows: DailyMetricOut[] }) {
  const today = todayISO();
  const points = (sel: (r: DailyMetricOut) => number | null): DatedPoint[] =>
    rows.map((r) => ({ date: r.date, value: sel(r) }));

  const hrv = points((r) => r.hrv_rmssd);
  const sleep = points((r) => r.sleep_score);
  const battery = points((r) => r.body_battery);
  const stress = points((r) => r.stress);

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<NoDataIcon />}
        title="Aucune donnée montre sur la période"
        hint="Connecte ta montre pour voir VFC, sommeil, body battery et stress."
      />
    );
  }

  const hrvStats = summarize(hrv.map((p) => p.value));
  const hrvMean7 = meanLastN(hrv, 7, today);
  const hrvMin = hrvStats.min !== null ? Math.floor(hrvStats.min - 5) : 0;
  const hrvMax = hrvStats.max !== null ? Math.ceil(hrvStats.max + 5) : 100;
  const lastRow = rows[rows.length - 1];
  const sleepDuration =
    lastRow.sleep_duration_min !== null ? formatDuration(lastRow.sleep_duration_min) : undefined;
  const recovery = recoveryBand(hrvMean7, hrvMin, hrvMax);

  return (
    <div className="flex flex-col gap-4">
      {/* Hero — dominant recovery signal (HRV 7-day average) */}
      <Card className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-52 w-52 rounded-full opacity-20 blur-3xl"
          style={{ background: recovery.color }}
        />
        <div className="relative">
          <CardTitle>Récupération · VFC sur 7 jours</CardTitle>
          <div className="mt-2 flex items-end gap-2">
            <span className="font-display nums text-[44px] leading-[0.9] text-stone-50">
              {hrvMean7 === null ? "—" : Math.round(hrvMean7)}
            </span>
            <span className="mb-1 text-sm text-stone-400">ms</span>
            <span className="mb-1 ml-auto font-display text-base" style={{ color: recovery.color }}>
              {recovery.word}
            </span>
          </div>
          <p className="mt-2 text-sm text-stone-400">
            Aujourd'hui{" "}
            <span className="nums text-stone-200">
              {latest(hrv) === null ? "—" : `${Math.round(latest(hrv) as number)} ms`}
            </span>{" "}
            · ta plage récente {hrvMin}–{hrvMax} ms
          </p>
        </div>
      </Card>

      {/* VFC — phase bar on the 7-day average */}
      <MetricCard
        title="VFC (HRV)"
        hint="RMSSD · moyenne 7 j · plus haut = mieux récupéré"
        color={METRIC_COLOR.hrv}
        points={hrv}
        today={today}
        unit=" ms"
        summary={<PhaseBar value={hrvMean7} min={hrvMin} max={hrvMax} unit=" ms" />}
      />

      {/* Sommeil — full ring + alarm-clock face */}
      <MetricCard
        title="Sommeil"
        hint="Score de la dernière nuit · /100"
        color={METRIC_COLOR.sleep}
        points={sleep}
        today={today}
        summary={
          <div className="flex justify-center">
            <RingGauge
              value={latest(sleep)}
              color={METRIC_COLOR.sleep}
              scoreLabel={sleepDuration ? `Dernière nuit · ${sleepDuration}` : "Dernière nuit"}
            />
          </div>
        }
      />

      {/* Body battery — open bottom arc */}
      <MetricCard
        title="Body battery"
        hint="Réserve d'énergie estimée · /100"
        color={METRIC_COLOR.body_battery}
        points={battery}
        today={today}
        summary={
          <div className="flex justify-center">
            <ArcGauge value={latest(battery)} color={METRIC_COLOR.body_battery} label="énergie" />
          </div>
        }
      />

      {/* Stress — day's average as a thermometer */}
      <MetricCard
        title="Stress (montre)"
        hint="Moyenne du jour · plus bas = mieux · /100"
        color={METRIC_COLOR.stress_watch}
        points={stress}
        today={today}
        summary={<Thermometer value={latest(stress)} caption="Moyenne mesurée aujourd'hui" />}
      />
    </div>
  );
}

function latest(points: DatedPoint[]): number | null {
  for (let i = points.length - 1; i >= 0; i--) if (points[i].value !== null) return points[i].value;
  return null;
}

// Where the 7-day HRV average sits in the athlete's own range → recovery word
// and the matching phase colour (red under-recovered → green well recovered).
function recoveryBand(value: number | null, min: number, max: number): { word: string; color: string } {
  if (value === null) return { word: "—", color: "#6B7280" };
  const span = max - min || 1;
  const idx = Math.min(2, Math.max(0, Math.floor(((value - min) / span) * 3)));
  return { word: ["Sous-récupéré", "Modéré", "Bien récupéré"][idx], color: PHASE_COLORS[idx] };
}
