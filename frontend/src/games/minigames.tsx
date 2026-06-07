// The two neuromuscular mini-games used inside the Routine flow. Each is
// self-contained: it measures, persists via createMiniTest, then calls onDone.
// Adapted from the legacy MiniTestPage, restyled to the design system.

import { useCallback, useEffect, useRef, useState } from "react";
import { createMiniTest } from "../api/endpoints";
import { todayISO } from "../lib/date";

// --- Reaction-time tap game -------------------------------------------------
type ReactionPhase = "idle" | "waiting" | "go" | "tooSoon" | "done";
const TRIALS = 5;

export function ReactionGame({ onDone }: { onDone: () => void }) {
  const [phase, setPhase] = useState<ReactionPhase>("idle");
  const [times, setTimes] = useState<number[]>([]);
  const goAt = useRef(0);
  const timer = useRef<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const clearTimer = () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  };

  const armNext = useCallback(() => {
    setPhase("waiting");
    const delay = 1000 + Math.random() * 2500;
    timer.current = window.setTimeout(() => {
      goAt.current = performance.now();
      setPhase("go");
    }, delay);
  }, []);

  useEffect(() => () => clearTimer(), []);

  function start() {
    setTimes([]);
    setError(null);
    armNext();
  }

  function onTap() {
    if (phase === "waiting") {
      clearTimer();
      setPhase("tooSoon");
      return;
    }
    if (phase === "go") {
      const rt = performance.now() - goAt.current;
      const next = [...times, rt];
      setTimes(next);
      if (next.length >= TRIALS) setPhase("done");
      else armNext();
      return;
    }
    if (phase === "tooSoon") armNext();
  }

  async function submit() {
    if (times.length === 0) return;
    const mean = times.reduce((a, b) => a + b, 0) / times.length;
    const variance = times.reduce((a, b) => a + (b - mean) ** 2, 0) / times.length;
    setSaving(true);
    setError(null);
    try {
      await createMiniTest({
        date: todayISO(),
        reported_at: new Date().toISOString(),
        data: {
          type: "reaction",
          mean_rt_ms: Math.round(mean),
          sd_rt_ms: Math.round(Math.sqrt(variance)),
          n_taps: times.length,
        },
      });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Envoi impossible");
      setSaving(false);
    }
  }

  const colors: Record<ReactionPhase, string> = {
    idle: "bg-ink-700",
    waiting: "bg-rose-900",
    go: "bg-flame-500",
    tooSoon: "bg-amber-700",
    done: "bg-ink-700",
  };
  const text: Record<ReactionPhase, string> = {
    idle: "Démarrer",
    waiting: "Attends le orange…",
    go: "TAP !",
    tooSoon: "Trop tôt — tape pour réessayer",
    done: "Terminé",
  };

  const mean =
    times.length > 0 ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : null;

  return (
    <div className="flex flex-col gap-3">
      <GameHeader step="Mini-jeu 1 / 2" title="Réflexe" tagline="Tape dès que l'écran s'allume." />

      <button
        type="button"
        onClick={phase === "idle" || phase === "done" ? start : onTap}
        className={`flex h-64 select-none items-center justify-center rounded-2xl text-2xl font-bold text-ink-950 transition-colors ${colors[phase]}`}
      >
        {phase === "idle" || phase === "done" ? (phase === "done" ? "Recommencer" : "Démarrer") : text[phase]}
      </button>

      <p className="text-center text-sm text-stone-400">
        {times.length > 0
          ? `${times.length}/${TRIALS} essais${mean ? ` · ${mean} ms en moyenne` : ""}`
          : `${TRIALS} essais`}
      </p>

      {phase === "done" && (
        <button
          type="button"
          onClick={submit}
          disabled={saving}
          className="rounded-xl bg-flame-500 px-4 py-3 font-semibold text-ink-950 shadow-glow disabled:opacity-50"
        >
          {saving ? "…" : "Valider et continuer"}
        </button>
      )}
      {error && <p className="text-center text-sm text-red-400">{error}</p>}
    </div>
  );
}

// --- CMJ jump game (DeviceMotion, manual fallback) --------------------------
const G = 9.81;
const heightCm = (flightMs: number) => ((G * (flightMs / 1000) ** 2) / 8) * 100;

export function JumpGame({ onDone }: { onDone: () => void }) {
  const [flightMs, setFlightMs] = useState<number | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const motionSupported =
    typeof window !== "undefined" && typeof window.DeviceMotionEvent !== "undefined";

  async function measure() {
    setError(null);
    const anyEvent = window.DeviceMotionEvent as unknown as {
      requestPermission?: () => Promise<"granted" | "denied">;
    };
    if (typeof anyEvent?.requestPermission === "function") {
      try {
        const res = await anyEvent.requestPermission();
        if (res !== "granted") {
          setError("Capteur refusé — saisis le temps de vol manuellement.");
          return;
        }
      } catch {
        setError("Capteur indisponible — saisis le temps de vol manuellement.");
        return;
      }
    }

    setMeasuring(true);
    let inAir = false;
    let liftoff = 0;
    let captured: number | null = null;

    const handler = (e: DeviceMotionEvent) => {
      const a = e.accelerationIncludingGravity;
      if (!a) return;
      const mag = Math.sqrt((a.x ?? 0) ** 2 + (a.y ?? 0) ** 2 + (a.z ?? 0) ** 2);
      if (!inAir && mag < 3) {
        inAir = true;
        liftoff = performance.now();
      } else if (inAir && mag > 12) {
        captured = performance.now() - liftoff;
        finish();
      }
    };

    function finish() {
      window.removeEventListener("devicemotion", handler);
      setMeasuring(false);
      if (captured && captured > 80 && captured < 1200) setFlightMs(Math.round(captured));
      else setError("Saut non détecté — réessaie ou saisis manuellement.");
    }

    window.addEventListener("devicemotion", handler);
    window.setTimeout(finish, 8000);
  }

  async function submit() {
    if (flightMs === null) return;
    setSaving(true);
    setError(null);
    try {
      await createMiniTest({
        date: todayISO(),
        reported_at: new Date().toISOString(),
        data: {
          type: "jump",
          flight_time_ms: flightMs,
          height_cm: Number(heightCm(flightMs).toFixed(1)),
        },
      });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Envoi impossible");
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <GameHeader
        step="Mini-jeu 2 / 2"
        title="Détente"
        tagline="Téléphone en poche serrée, saute (CMJ). On mesure le temps de vol."
      />

      <button
        type="button"
        onClick={measure}
        disabled={measuring || !motionSupported}
        className="rounded-xl bg-flame-500 px-4 py-3 font-semibold text-ink-950 shadow-glow disabled:opacity-50"
      >
        {measuring ? "Saute maintenant…" : motionSupported ? "Mesurer un saut" : "Capteur indisponible"}
      </button>

      <label className="flex flex-col gap-1 text-sm text-stone-300">
        Temps de vol (ms) — manuel
        <input
          type="number"
          value={flightMs ?? ""}
          onChange={(e) => setFlightMs(e.target.value ? Number(e.target.value) : null)}
          placeholder="ex. 480"
          className="rounded-lg border border-ink-600 bg-ink-700 px-3 py-2 text-stone-100 outline-none focus:border-flame-500"
        />
      </label>

      {flightMs !== null && flightMs > 0 && (
        <p className="text-sm text-stone-300">≈ {heightCm(flightMs).toFixed(1)} cm</p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={flightMs === null || flightMs <= 0 || saving}
        className="rounded-xl border border-ink-500 px-4 py-3 font-semibold text-stone-100 disabled:opacity-40"
      >
        {saving ? "…" : "Valider et terminer"}
      </button>
      {error && <p className="text-center text-sm text-amber-400">{error}</p>}
    </div>
  );
}

function GameHeader({ step, title, tagline }: { step: string; title: string; tagline: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-flame-500">{step}</p>
      <h2 className="mt-0.5 text-lg font-bold text-stone-50">{title}</h2>
      <p className="mt-0.5 text-sm text-stone-400">{tagline}</p>
    </div>
  );
}
