import type { Signal } from "../api/types";

export function SignalCard({ signal }: { signal: Signal }) {
  const pct = Math.round(Math.min(1, Math.max(0, signal.severity)) * 100);
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-100">{signal.explanation}</p>
        <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
          {signal.key}
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="h-full rounded-full bg-slate-300" style={{ width: `${pct}%` }} />
      </div>
      {signal.evidence.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-slate-400">
          {signal.evidence.map((e, i) => (
            <li key={i}>· {e}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
