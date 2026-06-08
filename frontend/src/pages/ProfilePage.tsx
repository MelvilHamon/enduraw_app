import { Link } from "react-router-dom";
import { getToday } from "../api/endpoints";
import type { DailyRead, Signal } from "../api/types";
import { ArcGauge } from "../components/charts/Gauge";
import { ErrorBanner } from "../components/ErrorBanner";
import { SettingsIcon } from "../components/icons";
import { CardSkeleton, HeroSkeleton } from "../components/Skeleton";
import { Card, CardTitle, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

// Onglet 5 — Profil. A big central score with a plain-language explanation of
// what it means — no train/rest recommendation. Below: the gap between inputs
// and data, and any out-of-norm signals. Gear (top-right) → settings.
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

      {loading && (
        <div className="flex flex-col gap-4">
          <HeroSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}
      {error && <ErrorBanner message={error} onRetry={reload} />}
      {data && <Body read={data} />}
    </div>
  );
}

function Body({ read }: { read: DailyRead }) {
  const divergence = read.signals.find((s) => s.key === "divergence_subj_obj");
  const outOfNorm = read.signals.filter((s) => s.triggered && s.key !== "divergence_subj_obj");
  const scorePct = Math.round(Math.min(1, Math.max(0, read.composite_score)) * 100);
  const { color, word } = scoreBand(scorePct);

  return (
    <div className="flex flex-col gap-4">
      {/* Hero score — the whole point of the screen */}
      <Card className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-52 w-52 rounded-full opacity-20 blur-3xl"
          style={{ background: color }}
        />
        <div className="relative flex flex-col items-center py-2 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-400">
            Indice du jour
          </p>
          <div className="mt-1">
            <ArcGauge value={scorePct} color={color} />
          </div>
          <div className="-mt-2 font-display text-xl" style={{ color }}>
            {word}
          </div>
          <p className="mt-3 max-w-xs text-sm text-stone-400">
            Cet indice résume combien de tes signaux s'écartent de tes normes habituelles. À
            <span className="text-stone-200"> 0</span>, tout est dans la norme ; plus il monte, plus
            il y a de signaux à surveiller.
          </p>
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

// Colour + word for the score, without implying a train/rest recommendation.
function scoreBand(pct: number): { color: string; word: string } {
  if (pct < 34) return { color: "#22C55E", word: "Tout est au vert" };
  if (pct < 67) return { color: "#F59E0B", word: "Quelques signaux" };
  return { color: "#EF4444", word: "Plusieurs signaux" };
}

function divergenceText(signal: Signal | undefined): string {
  if (!signal || !signal.triggered) {
    return "Ton ressenti colle à ce que disent tes données.";
  }
  if (signal.direction === "subj_optimistic") {
    return "Tu te sens mieux que ce que disent tes données — attention à ne pas surcharger.";
  }
  if (signal.direction === "subj_pessimistic") {
    return "Tu te sens moins bien que ce que disent tes données — sois patient, ça remonte.";
  }
  return "Il y a un écart entre ton ressenti et tes données.";
}
