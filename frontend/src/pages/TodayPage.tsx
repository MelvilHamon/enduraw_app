import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getCheckinToday, getToday } from "../api/endpoints";
import type { DailyRead, Signal } from "../api/types";
import { RecoBadge } from "../components/RecoBadge";
import { SignalCard } from "../components/SignalCard";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";
import { useAsync } from "../hooks/useAsync";

interface TodayData {
  read: DailyRead;
  hasCheckin: boolean;
}

async function load(): Promise<TodayData> {
  const read = await getToday();
  let hasCheckin = true;
  try {
    await getCheckinToday();
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) hasCheckin = false;
    else throw err;
  }
  return { read, hasCheckin };
}

// Headline built from the subjective↔objective divergence — the "brain" of the app.
function divergenceHeadline(signal: Signal | undefined): string | null {
  if (!signal || !signal.triggered) return null;
  if (signal.direction === "subj_optimistic") {
    return "Tu te sens mieux que ce que dit ton corps.";
  }
  if (signal.direction === "subj_pessimistic") {
    return "Tu te sens moins bien que ce que dit ton corps.";
  }
  return "Écart entre ton ressenti et tes données.";
}

export function TodayPage() {
  const { data, error, loading, reload } = useAsync(load, []);

  if (loading) return <Spinner label="Lecture de ta readiness…" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  const { read, hasCheckin } = data;
  const divergence = read.signals.find((s) => s.key === "divergence_subj_obj");
  const headline = divergenceHeadline(divergence);
  const scorePct = Math.round(Math.min(1, Math.max(0, read.composite_score)) * 100);

  return (
    <div className="flex flex-col gap-5 py-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">{read.date}</p>
        <h1 className="mt-0.5 text-2xl font-bold leading-tight text-slate-100">
          {headline ?? "Ta readiness du jour"}
        </h1>
      </div>

      {!hasCheckin && (
        <Link
          to="/routine"
          className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-200"
        >
          Tu n'as pas encore fait ta routine aujourd'hui →
        </Link>
      )}

      <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex flex-col gap-2">
          <RecoBadge reco={read.readiness.reco} />
          <p className="text-sm text-slate-300">{read.readiness.explanation}</p>
        </div>
        <ScoreGauge pct={scorePct} />
      </div>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold text-slate-300">Pourquoi</h2>
        {read.readiness.top_2.length === 0 ? (
          <p className="text-sm text-slate-500">Aucun signal préoccupant aujourd'hui.</p>
        ) : (
          read.readiness.top_2.map((s) => <SignalCard key={s.key} signal={s} />)
        )}
      </section>

      {read.engine_state && <EngineSummary state={read.engine_state} />}
    </div>
  );
}

function ScoreGauge({ pct }: { pct: number }) {
  return (
    <div className="flex flex-col items-center">
      <div className="text-3xl font-bold text-slate-100">{pct}</div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">charge / 100</div>
    </div>
  );
}

function EngineSummary({ state }: { state: NonNullable<DailyRead["engine_state"]> }) {
  const items: [string, string][] = [
    ["Forme", state.form.toFixed(1)],
    ["Fitness", state.fitness.toFixed(1)],
    ["Fatigue", state.fatigue.toFixed(1)],
    ["ACWR", state.acwr !== null ? state.acwr.toFixed(2) : "—"],
  ];
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-300">Moteur (CoachAgent)</h2>
      <div className="grid grid-cols-4 gap-2 text-center">
        {items.map(([label, value]) => (
          <div key={label}>
            <div className="text-lg font-semibold text-slate-100">{value}</div>
            <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
