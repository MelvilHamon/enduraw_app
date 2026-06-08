import { getTimeseries, listDailyMetrics } from "../api/endpoints";
import type { DailyMetricOut, Timeseries } from "../api/types";
import { CompareTriple } from "../components/charts/CompareTriple";
import { SegmentedGauge } from "../components/charts/Gauge";
import { WeeklyBars, type WeeklyBar } from "../components/charts/WeeklyBars";
import { ErrorBanner } from "../components/ErrorBanner";
import { MetricCard } from "../components/MetricCard";
import { CardSkeleton, HeroSkeleton } from "../components/Skeleton";
import { Card, CardTitle, Chip, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, shortDate, todayISO, toISO } from "../lib/date";
import { acwrColor, METRIC_COLOR, VO2_SEGMENTS } from "../lib/palette";
import { triple, type DatedPoint } from "../lib/stats";

interface LoadData {
  ts: Timeseries;
  daily: DailyMetricOut[];
}

const WINDOW_DAYS = 180;

async function loadCharge(): Promise<LoadData> {
  const from = daysAgoISO(WINDOW_DAYS);
  const to = todayISO();
  const [ts, daily] = await Promise.all([
    getTimeseries(from, to, ["form", "acwr"]),
    listDailyMetrics(from, to),
  ]);
  return { ts, daily };
}

const byDate = (a: DatedPoint, b: DatedPoint) => a.date.localeCompare(b.date);

// Onglet 2 — Charge. VO2 max as a Garmin-style gauge, ACWR as weekly bars, and
// the Banister form as a "today vs 7-day" card like the Accueil inputs.
export function LoadPage() {
  const { data, error, loading, reload } = useAsync(loadCharge, []);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Charge" subtitle="Ta charge d'entraînement course à pied." />

      {loading && (
        <div className="flex flex-col gap-4">
          <HeroSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Body data={data} />}
    </div>
  );
}

function Body({ data }: { data: LoadData }) {
  const today = todayISO();
  const form = [...(data.ts.series.form ?? [])].sort(byDate);
  const acwr = [...(data.ts.series.acwr ?? [])].sort(byDate);
  const vo2: DatedPoint[] = data.daily
    .filter((d) => d.vo2max !== null)
    .map((d) => ({ date: d.date, value: d.vo2max }))
    .sort(byDate);

  const vo2Latest = lastNonNull(vo2);
  const vo2Delta = vo2Latest ? deltaOver(vo2, vo2Latest.date, 7) : null;
  const vo2Band = vo2Latest ? vo2BandOf(vo2Latest.value) : null;
  const weeks = weeklyAcwr(acwr, 6);

  return (
    <div className="flex flex-col gap-4">
      {/* VO2 max — the page hero */}
      <Card className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-52 w-52 rounded-full opacity-20 blur-3xl"
          style={{ background: vo2Band?.color ?? "#F97316" }}
        />
        <div className="relative">
          <div className="flex items-center justify-between gap-2">
            <CardTitle>VO2 max · estimation montre</CardTitle>
            {vo2Delta !== null && Math.abs(vo2Delta) >= 0.05 && (
              <Chip color={vo2Delta >= 0 ? "#22C55E" : "#F43F5E"}>
                {vo2Delta >= 0 ? "+" : "−"}
                {Math.abs(vo2Delta).toFixed(1)} / 7 j
              </Chip>
            )}
          </div>
          <div className="mt-2 flex justify-center">
            <SegmentedGauge
              value={vo2Latest ? vo2Latest.value : null}
              min={30}
              max={70}
              segments={VO2_SEGMENTS}
              centerLabel={vo2Latest ? vo2Latest.value.toFixed(1) : "—"}
              sublabel="ml/kg/min"
            />
          </div>
          {vo2Band && (
            <p className="text-center font-display text-lg" style={{ color: vo2Band.color }}>
              {vo2Band.word}
            </p>
          )}
        </div>
      </Card>

      {/* ACWR weekly bars */}
      <Card>
        <CardTitle>ACWR par semaine</CardTitle>
        <p className="mt-1 text-xs text-stone-400">Charge aiguë / chronique · zone sûre 0,8–1,3</p>
        <div className="mt-2">
          <WeeklyBars bars={weeks} band={{ from: 0.8, to: 1.3 }} decimals={2} />
        </div>
      </Card>

      {/* Banister form — same card pattern as Accueil */}
      <MetricCard
        title="Forme (calculée)"
        hint="Modèle Banister · positif = frais, négatif = chargé"
        color={METRIC_COLOR.form}
        points={form}
        today={today}
        decimals={1}
        summary={
          <CompareTriple
            {...triple(form, today)}
            color={METRIC_COLOR.form}
            decimals={1}
            signed
          />
        }
      />
    </div>
  );
}

// Map a VO2 value to its Garmin-ladder band: a word + the segment's colour.
function vo2BandOf(v: number): { word: string; color: string } {
  const words = ["Faible", "Correct", "Bon", "Excellent", "Supérieur"];
  for (let i = 0; i < VO2_SEGMENTS.length; i++) {
    if (v < VO2_SEGMENTS[i].to) return { word: words[i], color: VO2_SEGMENTS[i].color };
  }
  const last = VO2_SEGMENTS.length - 1;
  return { word: words[last], color: VO2_SEGMENTS[last].color };
}

function lastNonNull(points: DatedPoint[]): { date: string; value: number } | null {
  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i].value !== null) return { date: points[i].date, value: points[i].value as number };
  }
  return null;
}

// Change between the latest value and the most recent value at least `days`
// before it (so VO2 "+0.2 / -0.7 over 7 days").
function deltaOver(points: DatedPoint[], latestDate: string, days: number): number | null {
  const latest = lastNonNull(points);
  if (!latest) return null;
  const target = toISO(new Date(new Date(`${latestDate}T00:00:00`).getTime() - days * 86400000));
  let prev: number | null = null;
  for (const p of points) if (p.value !== null && p.date <= target) prev = p.value;
  return prev === null ? null : latest.value - prev;
}

// Bucket the daily ACWR series into Monday-anchored weeks; keep the last `n`.
function weeklyAcwr(points: DatedPoint[], n: number): WeeklyBar[] {
  const buckets = new Map<string, number[]>();
  for (const p of points) {
    if (p.value === null) continue;
    const wk = weekStart(p.date);
    (buckets.get(wk) ?? buckets.set(wk, []).get(wk)!).push(p.value);
  }
  const keys = [...buckets.keys()].sort().slice(-n);
  return keys.map((wk) => {
    const vals = buckets.get(wk)!;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    return { label: shortDate(wk), value: avg, color: acwrColor(avg) };
  });
}

function weekStart(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  const diff = (d.getDay() + 6) % 7; // days since Monday
  d.setDate(d.getDate() - diff);
  return toISO(d);
}
