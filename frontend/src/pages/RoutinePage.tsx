import { useState } from "react";
import { ApiError } from "../api/client";
import { getCheckinToday, upsertCheckin } from "../api/endpoints";
import type { CheckinOut } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { SwipeCard, type SwipeStep } from "../components/SwipeCard";
import { Card, CardTitle, PageHeader } from "../components/ui";
import { JumpGame, ReactionGame } from "../games/minigames";
import { useAsync } from "../hooks/useAsync";
import { todayISO } from "../lib/date";

const TUTO_KEY = "enduraw.routine.tutoSeen";

// Cards in spec order. `encode` maps the -2..+2 gesture to the stored value.
const STEPS: (SwipeStep & { encode: (v: number) => number })[] = [
  {
    key: "form",
    title: "Forme",
    prompt: "Comment tu te sens vs d'habitude ?",
    cue: "Évalue ta forme",
    encode: (v) => v,
  },
  {
    // Fatigue is stored and shown on a 1..5 absolute scale (1 frais → 5 épuisé),
    // so the swipe shows that scale directly instead of the −2..+2 of the others.
    key: "fatigue",
    title: "Fatigue",
    prompt: "Ton niveau de fatigue aujourd'hui",
    cue: "Évalue ta fatigue",
    display: (v) => String(v + 3), // gesture −2..+2 → 1..5
    encode: (v) => v + 3, // stored 1..5
  },
  {
    key: "motivation",
    title: "Motivation",
    prompt: "Ton envie de t'entraîner vs d'habitude",
    cue: "Évalue ta motivation",
    encode: (v) => v,
  },
  {
    key: "stress",
    title: "Stress",
    prompt: "Ton stress vs d'habitude",
    cue: "Évalue ton stress",
    encode: (v) => v,
  },
];

async function loadCheckin(): Promise<CheckinOut | null> {
  try {
    return await getCheckinToday();
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function RoutinePage() {
  const { data, error, loading, reload } = useAsync(loadCheckin, []);
  const [redo, setRedo] = useState(false);

  if (loading) return <Spinner label="Chargement de ta routine…" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;

  // Routine already done today → recap, unless the athlete chose to redo it.
  if (data && !redo) {
    return <Recap checkin={data} onRedo={() => setRedo(true)} />;
  }

  return (
    <Flow
      onComplete={() => {
        setRedo(false);
        reload();
      }}
    />
  );
}

type Phase = "intro" | "cards" | "reaction" | "jump";

function Flow({ onComplete }: { onComplete: () => void }) {
  const firstTime = typeof localStorage !== "undefined" && localStorage.getItem(TUTO_KEY) === null;
  const [phase, setPhase] = useState<Phase>(firstTime ? "intro" : "cards");
  const [stepIdx, setStepIdx] = useState(0);
  const [values, setValues] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startCards() {
    try {
      localStorage.setItem(TUTO_KEY, "1");
    } catch {
      /* ignore */
    }
    setPhase("cards");
  }

  async function pick(value: number) {
    const step = STEPS[stepIdx];
    const next = { ...values, [step.key]: step.encode(value) };
    setValues(next);

    if (stepIdx < STEPS.length - 1) {
      setStepIdx((i) => i + 1);
      return;
    }
    // Last card → persist the check-in, then move to the mini-games.
    setBusy(true);
    setError(null);
    try {
      await upsertCheckin({
        date: todayISO(),
        form_vs_normal: next.form,
        motivation: next.motivation,
        fatigue: next.fatigue,
        stress: next.stress ?? null,
      });
      setPhase("reaction");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enregistrement impossible");
      setBusy(false);
    }
  }

  if (phase === "intro") return <Intro onStart={startCards} />;

  if (phase === "cards") {
    return (
      <div className="flex flex-col gap-5 py-2">
        <PageHeader title="Routine" subtitle="Renseigne ton ressenti, carte par carte." />
        {busy ? (
          <Spinner label="Enregistrement…" />
        ) : (
          <SwipeCard step={STEPS[stepIdx]} index={stepIdx} total={STEPS.length} onPick={pick} />
        )}
        {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}
      </div>
    );
  }

  if (phase === "reaction") {
    return (
      <div className="flex flex-col gap-5 py-2">
        <PageHeader title="Routine" subtitle="Place aux mini-jeux." />
        <ReactionGame onDone={() => setPhase("jump")} />
      </div>
    );
  }

  // phase === "jump"
  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Routine" subtitle="Dernier effort !" />
      <JumpGame onDone={onComplete} />
    </div>
  );
}

function Intro({ onStart }: { onStart: () => void }) {
  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Ta routine" subtitle="30 secondes, chaque matin." />
      <Card>
        <CardTitle>Comment ça marche</CardTitle>
        <p className="mt-3 text-sm text-stone-300">
          Une carte par ressenti. Tu réponds d'un geste :
        </p>
        <ul className="mt-3 grid grid-cols-2 gap-2 text-sm">
          {[
            ["↑ haut", "bien plus"],
            ["→ droite", "un peu plus"],
            ["↓ bas", "bien moins"],
            ["← gauche", "un peu moins"],
          ].map(([g, m]) => (
            <li key={g} className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-900 px-3 py-2">
              <span className="font-display text-stone-100">{g}</span>
              <span className="text-stone-400">{m}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-stone-400">
          Double-tap = comme d'habitude. Puis 2 mini-jeux : réflexe et détente.
        </p>
      </Card>
      <button
        type="button"
        onClick={onStart}
        className="rounded-xl bg-flame-500 px-4 py-3 font-semibold text-ink-950 shadow-glow"
      >
        C'est parti
      </button>
    </div>
  );
}

function Recap({ checkin, onRedo }: { checkin: CheckinOut; onRedo: () => void }) {
  const items: [string, string][] = [
    ["Forme", signed(checkin.form_vs_normal)],
    ["Fatigue", `${checkin.fatigue}/5`],
    ["Motivation", signed(checkin.motivation)],
    ["Stress", checkin.stress === null || checkin.stress === undefined ? "—" : signed(checkin.stress)],
  ];
  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Routine faite ✓" subtitle="Ton ressenti du jour est enregistré." />
      <Card>
        <div className="grid grid-cols-4 gap-2 text-center">
          {items.map(([label, value]) => (
            <div key={label}>
              <div className="font-display nums text-2xl text-flame-500">{value}</div>
              <div className="mt-0.5 text-[10px] uppercase tracking-wide text-stone-400">{label}</div>
            </div>
          ))}
        </div>
      </Card>
      <button
        type="button"
        onClick={onRedo}
        className="rounded-xl border border-ink-500 px-4 py-3 font-semibold text-stone-100"
      >
        Refaire la routine
      </button>
    </div>
  );
}

const signed = (v: number) => (v > 0 ? `+${v}` : `${v}`);
