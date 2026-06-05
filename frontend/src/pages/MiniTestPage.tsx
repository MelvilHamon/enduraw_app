import { useCallback, useEffect, useRef, useState } from "react";
import { createMiniTest, getBaseline } from "../api/endpoints";
import type { MiniTestBaseline, MiniTestType } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import { todayISO } from "../lib/date";

export function MiniTestPage() {
  const [tab, setTab] = useState<MiniTestType>("reaction");
  return (
    <div className="flex flex-col gap-5 py-2">
      <h1 className="text-xl font-bold text-slate-100">Mini-tests</h1>
      <div className="flex gap-2">
        {(["reaction", "jump"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex-1 rounded-full px-4 py-1.5 text-sm ${
              tab === t ? "bg-slate-100 text-slate-900" : "bg-slate-800 text-slate-300"
            }`}
          >
            {t === "reaction" ? "Temps de réaction" : "Saut (CMJ)"}
          </button>
        ))}
      </div>
      {tab === "reaction" ? <ReactionTest /> : <JumpTest />}
    </div>
  );
}

function BaselineHint({ type, nonce }: { type: MiniTestType; nonce: number }) {
  const { data } = useAsync<MiniTestBaseline>(() => getBaseline(type), [type, nonce]);
  if (!data || data.n === 0) return null;
  const z = data.latest_z;
  return (
    <p className="text-xs text-slate-400">
      Baseline {data.metric} : moyenne {data.mean?.toFixed(0) ?? "—"} sur {data.n} tests
      {z !== null ? ` · dernier z = ${z.toFixed(2)}` : ""}
    </p>
  );
}

// --- Reaction-time tap test -------------------------------------------------
type ReactionPhase = "idle" | "waiting" | "go" | "tooSoon" | "done";
const TRIALS = 5;

function ReactionTest() {
  const [phase, setPhase] = useState<ReactionPhase>("idle");
  const [times, setTimes] = useState<number[]>([]);
  const goAt = useRef(0);
  const timer = useRef<number | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

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
    setSaved(null);
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
    if (phase === "tooSoon") {
      armNext();
    }
  }

  async function submit() {
    if (times.length === 0) return;
    const mean = times.reduce((a, b) => a + b, 0) / times.length;
    const variance = times.reduce((a, b) => a + (b - mean) ** 2, 0) / times.length;
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
      setSaved(`Enregistré : ${Math.round(mean)} ms (n=${times.length})`);
      setPhase("idle");
      setNonce((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Envoi impossible");
    }
  }

  const colors: Record<ReactionPhase, string> = {
    idle: "bg-slate-800",
    waiting: "bg-rose-900",
    go: "bg-green-600",
    tooSoon: "bg-amber-700",
    done: "bg-slate-800",
  };
  const text: Record<ReactionPhase, string> = {
    idle: "Démarre le test",
    waiting: "Attends le vert…",
    go: "TAP !",
    tooSoon: "Trop tôt — tape pour réessayer",
    done: "Terminé",
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-slate-400">
        Tape dès que l'écran passe au vert. {TRIALS} essais.
      </p>
      <BaselineHint type="reaction" nonce={nonce} />

      <button
        type="button"
        onClick={phase === "idle" || phase === "done" ? start : onTap}
        className={`flex h-56 items-center justify-center rounded-2xl text-2xl font-bold text-white ${colors[phase]}`}
      >
        {phase === "idle" || phase === "done" ? "Démarrer" : text[phase]}
      </button>

      {times.length > 0 && (
        <p className="text-sm text-slate-300">
          Essais : {times.map((t) => Math.round(t)).join(" · ")} ms
        </p>
      )}

      {phase === "done" && (
        <button
          type="button"
          onClick={submit}
          className="rounded-xl bg-slate-100 px-4 py-3 font-semibold text-slate-900"
        >
          Enregistrer le résultat
        </button>
      )}

      {saved && <p className="text-sm text-green-400">{saved}</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}

// --- CMJ jump test (DeviceMotion, with manual fallback) ---------------------
const G = 9.81;

function heightCm(flightMs: number): number {
  const t = flightMs / 1000;
  return (G * t * t) / 8 * 100;
}

function JumpTest() {
  const [flightMs, setFlightMs] = useState<number | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const motionSupported =
    typeof window !== "undefined" && typeof window.DeviceMotionEvent !== "undefined";

  async function measure() {
    setError(null);
    setSaved(null);
    // iOS Safari requires an explicit permission request from a user gesture.
    const anyEvent = window.DeviceMotionEvent as unknown as {
      requestPermission?: () => Promise<"granted" | "denied">;
    };
    if (typeof anyEvent?.requestPermission === "function") {
      try {
        const res = await anyEvent.requestPermission();
        if (res !== "granted") {
          setError("Permission capteur refusée — saisis le temps de vol manuellement.");
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
      // Free-fall: total acceleration collapses toward 0g.
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
      if (captured && captured > 80 && captured < 1200) {
        setFlightMs(Math.round(captured));
      } else {
        setError("Saut non détecté — réessaie ou saisis manuellement.");
      }
    }

    window.addEventListener("devicemotion", handler);
    // Safety timeout: stop listening after 8s.
    window.setTimeout(finish, 8000);
  }

  async function submit() {
    if (flightMs === null) return;
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
      setSaved(`Enregistré : ${flightMs} ms → ${heightCm(flightMs).toFixed(1)} cm`);
      setFlightMs(null);
      setNonce((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Envoi impossible");
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-slate-400">
        Place le téléphone dans une poche serrée et saute (counter-movement jump). On mesure
        le temps de vol.
      </p>
      <BaselineHint type="jump" nonce={nonce} />

      <button
        type="button"
        onClick={measure}
        disabled={measuring || !motionSupported}
        className="rounded-xl bg-slate-100 px-4 py-3 font-semibold text-slate-900 disabled:opacity-50"
      >
        {measuring ? "Saute maintenant…" : motionSupported ? "Mesurer un saut" : "Capteur indisponible"}
      </button>

      <label className="flex flex-col gap-1 text-sm text-slate-300">
        Temps de vol (ms) — manuel / stub
        <input
          type="number"
          value={flightMs ?? ""}
          onChange={(e) => setFlightMs(e.target.value ? Number(e.target.value) : null)}
          placeholder="ex. 480"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
        />
      </label>

      {flightMs !== null && flightMs > 0 && (
        <p className="text-sm text-slate-300">≈ {heightCm(flightMs).toFixed(1)} cm</p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={flightMs === null || flightMs <= 0}
        className="rounded-xl border border-slate-600 px-4 py-3 font-semibold text-slate-100 disabled:opacity-40"
      >
        Enregistrer le saut
      </button>

      {saved && <p className="text-sm text-green-400">{saved}</p>}
      {error && <p className="text-sm text-amber-400">{error}</p>}
    </div>
  );
}
