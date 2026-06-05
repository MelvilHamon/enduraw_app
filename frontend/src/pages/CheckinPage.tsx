import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Segmented } from "../components/Segmented";
import { upsertCheckin } from "../api/endpoints";
import { todayISO } from "../lib/date";

// Comparative phrasing — "vs un jour normal" is the whole point of form_vs_normal.
const FORM_OPTIONS = [
  { value: -2, label: "−−", sub: "Bien pire" },
  { value: -1, label: "−", sub: "Un peu pire" },
  { value: 0, label: "=", sub: "Normal" },
  { value: 1, label: "+", sub: "Un peu mieux" },
  { value: 2, label: "++", sub: "Bien mieux" },
];

const SCALE_1_5 = [1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }));

export function CheckinPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<number | null>(null);
  const [motivation, setMotivation] = useState<number | null>(null);
  const [fatigue, setFatigue] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const complete = form !== null && motivation !== null && fatigue !== null;

  async function submit() {
    if (!complete) return;
    setBusy(true);
    setError(null);
    try {
      await upsertCheckin({
        date: todayISO(),
        form_vs_normal: form,
        motivation,
        fatigue,
      });
      navigate("/today", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enregistrement impossible");
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 py-2">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Check-in du jour</h1>
        <p className="text-sm text-slate-400">3 taps, ~15 secondes.</p>
      </div>

      <Segmented
        title="Forme"
        hint="Comment tu te sens, vs un jour normal ?"
        options={FORM_OPTIONS}
        value={form}
        onChange={setForm}
      />
      <Segmented
        title="Motivation"
        hint="1 = aucune · 5 = à fond"
        options={SCALE_1_5}
        value={motivation}
        onChange={setMotivation}
      />
      <Segmented
        title="Fatigue"
        hint="1 = frais · 5 = épuisé"
        options={SCALE_1_5}
        value={fatigue}
        onChange={setFatigue}
      />

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={submit}
        disabled={!complete || busy}
        className="rounded-xl bg-slate-100 px-4 py-3 font-semibold text-slate-900 disabled:opacity-40"
      >
        {busy ? "Enregistrement…" : "Valider le check-in"}
      </button>
    </div>
  );
}
