import { useState, type ReactNode } from "react";
import { addReport, createNiggle, getNiggle, listNiggles } from "../api/endpoints";
import type {
  IsNewOrRecurrent,
  MechanicalPattern,
  NiggleWithReports,
  PainType,
  Side,
  Timing,
} from "../api/types";
import { BodyMap, type BodyZone } from "../components/BodyMap";
import { ErrorBanner } from "../components/ErrorBanner";
import { LineChart } from "../components/LineChart";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import { todayISO } from "../lib/date";
import { REGION_LABEL } from "../lib/labels";

const PAIN_TYPES: PainType[] = ["sharp", "dull", "tension", "burning", "stabbing"];
const TIMINGS: Timing[] = ["during", "after", "morning_stiffness", "constant"];
const PATTERNS: MechanicalPattern[] = ["uphill", "downhill", "push_off", "impact", "rest", "constant"];

export function BodyMapPage() {
  const { data: niggles, error, loading, reload } = useAsync(() => listNiggles(true), []);
  const [zone, setZone] = useState<BodyZone | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const highlighted = new Set((niggles ?? []).map((n) => `${n.region}:${n.side}`));

  return (
    <div className="flex flex-col gap-5 py-2">
      <h1 className="text-xl font-bold text-slate-100">Carte du corps</h1>

      <BodyMap highlighted={highlighted} onSelect={setZone} />

      {zone && (
        <NiggleForm
          zone={zone}
          onCancel={() => setZone(null)}
          onSaved={() => {
            setZone(null);
            reload();
          }}
        />
      )}

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold text-slate-300">Gênes actives</h2>
        {loading && <Spinner />}
        {error && <ErrorBanner message={error} onRetry={reload} />}
        {niggles && niggles.length === 0 && (
          <p className="text-sm text-slate-500">Aucune gêne active. 🎉</p>
        )}
        {niggles?.map((n) => (
          <NiggleRow
            key={n.id}
            id={n.id}
            label={`${REGION_LABEL[n.region]}${n.side !== "center" ? ` (${n.side})` : ""}`}
            expanded={expanded === n.id}
            onToggle={() => setExpanded(expanded === n.id ? null : n.id)}
            onReported={reload}
          />
        ))}
      </section>
    </div>
  );
}

function NiggleForm({
  zone,
  onCancel,
  onSaved,
}: {
  zone: BodyZone;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [side, setSide] = useState<Side>(zone.side);
  const [intensity, setIntensity] = useState(3);
  const [painType, setPainType] = useState<PainType | "">("");
  const [timing, setTiming] = useState<Timing | "">("");
  const [pattern, setPattern] = useState<MechanicalPattern | "">("");
  const [history, setHistory] = useState<IsNewOrRecurrent>("new");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await createNiggle({
        region: zone.region,
        side,
        opened_at: todayISO(),
        notes: notes || null,
        initial_report: {
          date: todayISO(),
          intensity,
          pain_type: painType || null,
          timing: timing || null,
          mechanical_pattern: pattern || null,
          is_new_or_recurrent: history,
          notes: notes || null,
        },
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Création impossible");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900 p-4">
      <h3 className="text-base font-semibold text-slate-100">
        Nouvelle gêne — {REGION_LABEL[zone.region]}
      </h3>

      <div className="mt-3 flex flex-col gap-3 text-sm">
        <Field label="Côté">
          <Select value={side} onChange={(v) => setSide(v as Side)} options={["left", "right", "center", "bilateral"]} />
        </Field>

        <Field label={`Intensité : ${intensity}/10`}>
          <input
            type="range"
            min={0}
            max={10}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            className="w-full"
          />
        </Field>

        <Field label="Type de douleur">
          <Select value={painType} onChange={(v) => setPainType(v as PainType)} options={["", ...PAIN_TYPES]} />
        </Field>
        <Field label="Quand">
          <Select value={timing} onChange={(v) => setTiming(v as Timing)} options={["", ...TIMINGS]} />
        </Field>
        <Field label="Mouvement déclencheur">
          <Select value={pattern} onChange={(v) => setPattern(v as MechanicalPattern)} options={["", ...PATTERNS]} />
        </Field>
        <Field label="Historique">
          <Select
            value={history}
            onChange={(v) => setHistory(v as IsNewOrRecurrent)}
            options={["new", "recurrent", "unknown"]}
          />
        </Field>
        <Field label="Notes">
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100"
          />
        </Field>

        {error && <p className="text-red-400">{error}</p>}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            className="flex-1 rounded-lg bg-slate-100 px-3 py-2 font-semibold text-slate-900 disabled:opacity-50"
          >
            {busy ? "…" : "Signaler"}
          </button>
          <button type="button" onClick={onCancel} className="rounded-lg border border-slate-700 px-3 py-2 text-slate-300">
            Annuler
          </button>
        </div>
      </div>
    </div>
  );
}

function NiggleRow({
  id,
  label,
  expanded,
  onToggle,
  onReported,
}: {
  id: string;
  label: string;
  expanded: boolean;
  onToggle: () => void;
  onReported: () => void;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-slate-200">
        <span>{label}</span>
        <span className="text-slate-500">{expanded ? "▾" : "▸"}</span>
      </button>
      {expanded && <NiggleDetail id={id} onReported={onReported} />}
    </div>
  );
}

function NiggleDetail({ id, onReported }: { id: string; onReported: () => void }) {
  const { data, error, loading, reload } = useAsync<NiggleWithReports>(() => getNiggle(id), [id]);
  const [intensity, setIntensity] = useState(3);
  const [busy, setBusy] = useState(false);

  async function quickReport() {
    setBusy(true);
    try {
      await addReport(id, { date: todayISO(), intensity, is_new_or_recurrent: "recurrent" });
      reload();
      onReported();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Spinner />;
  if (error) return <div className="px-3 pb-3"><ErrorBanner message={error} onRetry={reload} /></div>;
  if (!data) return null;

  const points = data.reports.map((r) => ({ date: r.date, value: r.intensity }));

  return (
    <div className="border-t border-slate-800 px-3 py-3">
      {points.length >= 2 ? (
        <LineChart series={[{ name: "Intensité", color: "#f87171", points }]} height={110} />
      ) : (
        <p className="text-xs text-slate-500">
          {points.length === 1 ? `Dernière intensité : ${points[0].value}/10` : "Aucun report."}
        </p>
      )}

      <div className="mt-3 flex items-center gap-2">
        <input
          type="range"
          min={0}
          max={10}
          value={intensity}
          onChange={(e) => setIntensity(Number(e.target.value))}
          className="flex-1"
        />
        <button
          type="button"
          onClick={quickReport}
          disabled={busy}
          className="rounded-lg bg-slate-100 px-3 py-1.5 text-sm font-semibold text-slate-900 disabled:opacity-50"
        >
          + Report ({intensity})
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-slate-300">
      <span className="text-xs text-slate-400">{label}</span>
      {children}
    </label>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100"
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o === "" ? "—" : o}
        </option>
      ))}
    </select>
  );
}
