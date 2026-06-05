import { useState } from "react";
import { getIllnessHint, getTimeseries, postIllness } from "../api/endpoints";
import type { IllnessHint, IllnessSymptom, Timeseries } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { LineChart } from "../components/LineChart";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";

const WINDOW_DAYS = 60;

const SYMPTOM_LABEL: Record<IllnessSymptom, string> = {
  sore_throat: "Mal de gorge",
  congestion: "Congestion",
  fever: "Fièvre",
  unusual_fatigue: "Fatigue inhabituelle",
  cough: "Toux",
  body_aches: "Courbatures",
};

export function InsightsPage() {
  return (
    <div className="flex flex-col gap-6 py-2">
      <h1 className="text-xl font-bold text-slate-100">Courbes</h1>
      <IllnessPrompt />
      <TimeseriesCharts />
    </div>
  );
}

function TimeseriesCharts() {
  const { data, error, loading, reload } = useAsync<Timeseries>(
    () => getTimeseries(daysAgoISO(WINDOW_DAYS), todayISO(), ["form"]),
    [],
  );

  if (loading) return <Spinner label="Chargement des séries…" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  const engineForm = data.series.form ?? [];

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-1 text-sm font-semibold text-slate-300">Forme moteur (Banister)</h2>
        <LineChart series={[{ name: "form (moteur)", color: "#38bdf8", points: engineForm }]} />
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-1 text-sm font-semibold text-slate-300">Ressenti & divergence</h2>
        <p className="mb-2 text-xs text-slate-500">
          Ton ressenti (−2..+2) vs l'écart z subjectif − objectif. Une divergence positive =
          tu te sens mieux que tes données.
        </p>
        <LineChart
          zeroLine
          series={[
            { name: "ressenti", color: "#a78bfa", points: data.form_vs_normal },
            { name: "divergence Δ", color: "#f59e0b", points: data.divergence },
          ]}
        />
      </section>
    </div>
  );
}

function IllnessPrompt() {
  const { data, loading, reload } = useAsync<IllnessHint>(() => getIllnessHint(todayISO()), []);
  const [selected, setSelected] = useState<Set<IllnessSymptom>>(new Set());
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading || !data) return null;

  if (done) {
    return (
      <div className="rounded-2xl border border-green-800 bg-green-950/50 p-4 text-sm text-green-200">
        Symptômes enregistrés. Prends soin de toi. 🤒
      </div>
    );
  }

  if (!data.triggered) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-xs text-slate-500">
        Pas d'alerte maladie aujourd'hui (vs ta baseline sur {data.baseline_window_days} j).
      </div>
    );
  }

  function toggle(s: IllnessSymptom) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }

  async function confirm() {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      await postIllness({ date: todayISO(), symptoms: [...selected] });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Envoi impossible");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-amber-700 bg-amber-950/40 p-4">
      <h2 className="text-sm font-semibold text-amber-200">Signaux physiologiques inhabituels</h2>
      <p className="mt-1 text-xs text-amber-200/80">
        Tes données (HRV/FC repos/respiration) s'écartent de ta normale. Des symptômes ?
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {(Object.keys(SYMPTOM_LABEL) as IllnessSymptom[]).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => toggle(s)}
            className={`rounded-full px-3 py-1 text-xs ${
              selected.has(s) ? "bg-amber-300 text-amber-950" : "bg-amber-900/60 text-amber-100"
            }`}
          >
            {SYMPTOM_LABEL[s]}
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={confirm}
          disabled={selected.size === 0 || busy}
          className="rounded-lg bg-amber-300 px-3 py-2 text-sm font-semibold text-amber-950 disabled:opacity-50"
        >
          {busy ? "…" : "Confirmer les symptômes"}
        </button>
        <button
          type="button"
          onClick={() => reload()}
          className="rounded-lg border border-amber-700 px-3 py-2 text-sm text-amber-200"
        >
          Aucun symptôme
        </button>
      </div>
    </div>
  );
}
