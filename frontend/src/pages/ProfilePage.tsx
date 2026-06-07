import { Link } from "react-router-dom";
import { getToday } from "../api/endpoints";
import type { DailyRead, Signal } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { SettingsIcon } from "../components/icons";
import { Spinner } from "../components/Spinner";
import { Card, CardTitle, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { RECO_BG, RECO_LABEL } from "../lib/labels";

// Onglet 5 — Profil. The athlete's health state in clear terms: overall
// recommendation, the gap between their inputs and their data, and any
// out-of-norm signals. Gear (top-right) → settings to connect a watch.
export function ProfilePage() {
  const { data, error, loading, reload } = useAsync<DailyRead>(() => getToday(), []);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader
        title="Profil"
        subtitle="Ton état de santé, en clair."
        action={
          <Link
            to="/settings"
            aria-label="Paramètres"
            className="rounded-full border border-ink-600 p-2 text-stone-400 hover:text-flame-500"
          >
            <SettingsIcon />
          </Link>
        }
      />

      {loading && <Spinner label="Lecture de ton état…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}
      {data && <Body read={data} />}
    </div>
  );
}

function Body({ read }: { read: DailyRead }) {
  const divergence = read.signals.find((s) => s.key === "divergence_subj_obj");
  const outOfNorm = read.signals.filter((s) => s.triggered && s.key !== "divergence_subj_obj");
  const scorePct = Math.round(Math.min(1, Math.max(0, read.composite_score)) * 100);

  return (
    <div className="flex flex-col gap-4">
      {/* Overall state */}
      <Card>
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <span
              className={`inline-flex w-fit items-center rounded-full px-3 py-1 text-sm font-semibold text-white ${RECO_BG[read.readiness.reco]}`}
            >
              {RECO_LABEL[read.readiness.reco]}
            </span>
            <p className="text-sm text-stone-300">{read.readiness.explanation}</p>
          </div>
          <div className="flex flex-col items-center">
            <div className="text-3xl font-bold text-flame-500">{scorePct}</div>
            <div className="text-[10px] uppercase tracking-wide text-stone-500">score / 100</div>
          </div>
        </div>
      </Card>

      {/* Inputs vs data */}
      <Card>
        <CardTitle>Tes ressentis vs tes données</CardTitle>
        <p className="mt-2 text-sm text-stone-300">{divergenceText(divergence)}</p>
        {divergence?.triggered && divergence.evidence.length > 0 && (
          <ul className="mt-2 space-y-0.5 text-xs text-stone-500">
            {divergence.evidence.map((e, i) => (
              <li key={i}>· {e}</li>
            ))}
          </ul>
        )}
      </Card>

      {/* Out-of-norm signals */}
      <Card>
        <CardTitle>Signaux hors normes</CardTitle>
        {outOfNorm.length === 0 ? (
          <p className="mt-2 text-sm text-stone-400">Aucune métrique hors norme aujourd'hui. ✓</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3">
            {outOfNorm.map((s) => (
              <li key={s.key}>
                <p className="text-sm text-stone-100">{s.explanation}</p>
                {s.evidence.length > 0 && (
                  <ul className="mt-1 space-y-0.5 text-xs text-stone-500">
                    {s.evidence.map((e, i) => (
                      <li key={i}>· {e}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function divergenceText(signal: Signal | undefined): string {
  if (!signal || !signal.triggered) {
    return "Ton ressenti colle à ce que disent tes données. 👌";
  }
  if (signal.direction === "subj_optimistic") {
    return "Tu te sens mieux que ce que disent tes données — attention à ne pas surcharger.";
  }
  if (signal.direction === "subj_pessimistic") {
    return "Tu te sens moins bien que ce que disent tes données — sois patient, ça remonte.";
  }
  return "Il y a un écart entre ton ressenti et tes données.";
}
