// Gesture card for the Routine: the athlete enters a -2..+2 value by swiping.
//   right → +1   left → -1   up → +2   down → -2   double-tap → 0
// Pointer-based so it works with touch and mouse. Live drag feedback shows the
// candidate value before release.

import { useRef, useState } from "react";

export interface DirLabels {
  up: string; // +2
  right: string; // +1
  center: string; // 0
  left: string; // -1
  down: string; // -2
}

export interface SwipeStep {
  key: string;
  title: string;
  prompt: string;
  labels: DirLabels;
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

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wide text-flame-500">
          {index + 1} / {total}
        </p>
        <h2 className="mt-1 text-2xl font-bold text-stone-50">{step.title}</h2>
        <p className="mt-0.5 text-sm text-stone-400">{step.prompt}</p>
      </div>

      <div className="relative h-72 w-full max-w-xs select-none">
        {/* directional hints */}
        <Hint pos="top" active={cand === 2} label={step.labels.up} sign="+2" />
        <Hint pos="bottom" active={cand === -2} label={step.labels.down} sign="−2" />
        <Hint pos="left" active={cand === -1} label={step.labels.left} sign="−1" />
        <Hint pos="right" active={cand === 1} label={step.labels.right} sign="+1" />

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
          className="absolute inset-6 flex cursor-grab touch-none flex-col items-center justify-center rounded-3xl border border-ink-500 bg-ink-700 shadow-glow active:cursor-grabbing"
        >
          <span className="text-5xl font-black text-flame-500">{cand ?? "•"}</span>
          <span className="mt-2 text-sm text-stone-400">
            {cand === null ? "Glisse ou double-tape" : labelFor(step, cand)}
          </span>
        </div>
      </div>

      <p className="text-center text-xs text-stone-500">
        Glisse : haut +2 · droite +1 · gauche −1 · bas −2 · double-tap = normal
      </p>
    </div>
  );
}

function labelFor(step: SwipeStep, v: number): string {
  return v === 2
    ? step.labels.up
    : v === 1
      ? step.labels.right
      : v === 0
        ? step.labels.center
        : v === -1
          ? step.labels.left
          : step.labels.down;
}

function Hint({
  pos,
  label,
  sign,
  active,
}: {
  pos: "top" | "bottom" | "left" | "right";
  label: string;
  sign: string;
  active: boolean;
}) {
  const place = {
    top: "left-1/2 top-0 -translate-x-1/2",
    bottom: "left-1/2 bottom-0 -translate-x-1/2",
    left: "left-0 top-1/2 -translate-y-1/2",
    right: "right-0 top-1/2 -translate-y-1/2",
  }[pos];
  return (
    <div
      className={`pointer-events-none absolute ${place} flex flex-col items-center text-center text-[11px] transition-colors ${
        active ? "text-flame-500" : "text-stone-600"
      }`}
    >
      <span className="font-bold">{sign}</span>
      <span className="max-w-[72px] leading-tight">{label}</span>
    </div>
  );
}
