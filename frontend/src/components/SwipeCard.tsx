// Gesture card for the Routine: the athlete enters a value by swiping.
//   right → +1   left → -1   up → +2   down → -2   double-tap → 0
// Live drag feedback shows the candidate value as a single large number in the
// centre — mapped to each metric's own scale via `display`, so nothing overlaps.
// Pointer-based so it works with touch and mouse.

import { useRef, useState } from "react";

export interface SwipeStep {
  key: string;
  title: string;
  prompt: string;
  // Centre instruction shown before a swipe, e.g. "Évalue ta forme".
  cue: string;
  // Maps the -2..+2 gesture to the number shown to the athlete. Defaults to a
  // signed -2..+2 string; fatigue overrides it to its 1..5 scale.
  display?: (v: number) => string;
}

const SWIPE_THRESHOLD = 56; // px to commit a directional swipe
const TAP_MOVE = 12; // px max movement still counted as a tap
const DOUBLE_TAP_MS = 320;

function candidate(dx: number, dy: number): number | null {
  const ax = Math.abs(dx);
  const ay = Math.abs(dy);
  if (Math.max(ax, ay) < SWIPE_THRESHOLD) return null;
  if (ax > ay) return dx > 0 ? 1 : -1;
  return dy < 0 ? 2 : -2;
}

// Default signed rendering (uses a real minus sign). Fatigue overrides via `display`.
function signed(v: number): string {
  return v > 0 ? `+${v}` : v < 0 ? `−${Math.abs(v)}` : "0";
}

function dispOf(step: SwipeStep, v: number): string {
  return step.display ? step.display(v) : signed(v);
}

export function SwipeCard({
  step,
  index,
  total,
  onPick,
}: {
  step: SwipeStep;
  index: number;
  total: number;
  onPick: (value: number) => void;
}) {
  const [drag, setDrag] = useState({ x: 0, y: 0 });
  const start = useRef({ x: 0, y: 0 });
  const pid = useRef<number | null>(null);
  const lastTap = useRef(0);

  const cand = candidate(drag.x, drag.y);

  function onPointerDown(e: React.PointerEvent) {
    start.current = { x: e.clientX, y: e.clientY };
    pid.current = e.pointerId;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: React.PointerEvent) {
    if (pid.current === null) return;
    setDrag({ x: e.clientX - start.current.x, y: e.clientY - start.current.y });
  }

  function onPointerUp(e: React.PointerEvent) {
    if (pid.current === null) return;
    pid.current = null;
    const dx = e.clientX - start.current.x;
    const dy = e.clientY - start.current.y;
    setDrag({ x: 0, y: 0 });

    if (Math.abs(dx) < TAP_MOVE && Math.abs(dy) < TAP_MOVE) {
      const now = performance.now();
      if (now - lastTap.current < DOUBLE_TAP_MS) {
        lastTap.current = 0;
        onPick(0);
      } else {
        lastTap.current = now;
      }
      return;
    }
    const v = candidate(dx, dy);
    if (v !== null) onPick(v);
  }

  const rot = drag.x / 18;
  const side = sideOf(cand);
  const active = cand !== null && cand !== 0;

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-col items-center text-center">
        {/* step progress dots */}
        <div className="flex items-center gap-1.5">
          {Array.from({ length: total }).map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === index ? "w-5 bg-flame-500" : i < index ? "w-1.5 bg-flame-700" : "w-1.5 bg-ink-600"
              }`}
            />
          ))}
        </div>
        <h2 className="mt-3 font-display text-3xl text-stone-50">{step.title}</h2>
        <p className="mt-1 text-sm text-stone-400">{step.prompt}</p>
      </div>

      <div className="relative h-72 w-full max-w-xs select-none">
        {/* faint edge values for orientation (the active one yields to the card) */}
        <EdgeSign pos="top" sign={dispOf(step, 2)} hidden={cand === 2} />
        <EdgeSign pos="bottom" sign={dispOf(step, -2)} hidden={cand === -2} />
        <EdgeSign pos="left" sign={dispOf(step, -1)} hidden={cand === -1} />
        <EdgeSign pos="right" sign={dispOf(step, 1)} hidden={cand === 1} />

        {/* the draggable card */}
        <div
          role="slider"
          aria-label={step.title}
          aria-valuemin={-2}
          aria-valuemax={2}
          aria-valuenow={cand ?? 0}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onKeyDown={(e) => {
            const map: Record<string, number> = {
              ArrowUp: 2,
              ArrowRight: 1,
              ArrowDown: -2,
              ArrowLeft: -1,
              Enter: 0,
              " ": 0,
            };
            if (e.key in map) {
              e.preventDefault();
              onPick(map[e.key]);
            }
          }}
          style={{
            transform: `translate(${drag.x}px, ${drag.y}px) rotate(${rot}deg)`,
            transition: pid.current === null ? "transform 160ms ease-out" : "none",
            touchAction: "none",
          }}
          className="absolute inset-6 flex cursor-grab touch-none items-center justify-center overflow-hidden rounded-3xl border border-ink-500 bg-ink-700 shadow-glow active:cursor-grabbing"
        >
          {/* translucent arc glowing on the side being swiped toward */}
          <div
            aria-hidden
            className={`pointer-events-none absolute h-56 w-56 rounded-full bg-flame-500 blur-2xl transition-all duration-150 ${
              active ? "opacity-25" : "opacity-0"
            } ${arcPlace(side)}`}
          />

          {/* a single centred element: the instruction before a swipe, the big
              value once swiping — never both, so they can't overlap */}
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center">
            {cand === null ? (
              <span className="font-display text-2xl leading-tight text-stone-400">{step.cue}</span>
            ) : (
              <span className="font-display nums text-7xl text-flame-500">{dispOf(step, cand)}</span>
            )}
          </div>
        </div>
      </div>

      <p className="text-center text-xs text-stone-500">
        Glisse : haut {dispOf(step, 2)} · droite {dispOf(step, 1)} · gauche {dispOf(step, -1)} · bas{" "}
        {dispOf(step, -2)} · double-tap = normal
      </p>
    </div>
  );
}

type Side = "top" | "bottom" | "left" | "right" | null;

function sideOf(cand: number | null): Side {
  return cand === 2 ? "top" : cand === -2 ? "bottom" : cand === -1 ? "left" : cand === 1 ? "right" : null;
}

// Where the translucent arc sits (pushed off the swiped edge so only an arc shows).
function arcPlace(side: Side): string {
  switch (side) {
    case "top":
      return "-top-28 left-1/2 -translate-x-1/2";
    case "bottom":
      return "-bottom-28 left-1/2 -translate-x-1/2";
    case "left":
      return "-left-28 top-1/2 -translate-y-1/2";
    case "right":
      return "-right-28 top-1/2 -translate-y-1/2";
    default:
      return "left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0";
  }
}

function EdgeSign({ pos, sign, hidden }: { pos: "top" | "bottom" | "left" | "right"; sign: string; hidden: boolean }) {
  const place = {
    top: "left-1/2 top-0 -translate-x-1/2",
    bottom: "left-1/2 bottom-0 -translate-x-1/2",
    left: "left-0 top-1/2 -translate-y-1/2",
    right: "right-0 top-1/2 -translate-y-1/2",
  }[pos];
  return (
    <span
      className={`pointer-events-none absolute ${place} text-[11px] font-bold text-stone-700 transition-opacity ${
        hidden ? "opacity-0" : "opacity-100"
      }`}
    >
      {sign}
    </span>
  );
}
