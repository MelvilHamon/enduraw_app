// Restrained palette: orange is the single brand accent, neutral is the default
// for non-semantic curves, and colour is otherwise spent ONLY where it carries
// meaning (VO2 ladder, ACWR zones, stress ramp, recovery phases, score band,
// good/bad deltas). This avoids the "rainbow wall" and reads as a premium,
// instrument-like product.

export const ACCENT = "#F97316"; // brand orange (flame-500)
export const NEUTRAL_LINE = "#D6D3D1"; // stone-300 — calm default for plain curves

// Metric colour roles. Subjective inputs and plain trends use the neutral line;
// single-value gauges (sleep, body battery) carry the brand accent; semantic
// scales below recolour themselves and ignore these.
export const METRIC_COLOR = {
  form: NEUTRAL_LINE,
  fatigue: NEUTRAL_LINE,
  motivation: NEUTRAL_LINE,
  stress: NEUTRAL_LINE,
  reaction: NEUTRAL_LINE,
  jump: NEUTRAL_LINE,
  vo2: ACCENT, // gauge itself uses the Garmin segments
  acwr: ACCENT, // bars recolour per zone via acwrColor
  hrv: NEUTRAL_LINE, // phase bar carries the recovery meaning
  sleep: ACCENT, // single-fill ring → brand accent
  body_battery: ACCENT, // single-fill arc → brand accent
  stress_watch: NEUTRAL_LINE, // thermometer carries the calm→high ramp
} as const;

export type MetricKey = keyof typeof METRIC_COLOR;

// Garmin-style VO2 max ladder: red → orange → green → blue → violet.
// Each segment is [from, to) in ml/kg/min, lowest (worst) first.
export interface GaugeSegment {
  from: number;
  to: number;
  color: string;
}

export const VO2_SEGMENTS: GaugeSegment[] = [
  { from: 30, to: 38, color: "#EF4444" }, // red — poor
  { from: 38, to: 46, color: "#F97316" }, // orange — fair
  { from: 46, to: 54, color: "#22C55E" }, // green — good
  { from: 54, to: 62, color: "#3B82F6" }, // blue — excellent
  { from: 62, to: 70, color: "#A855F7" }, // violet — superior
];

// ACWR safe zone is 0.8–1.3. Colour a bar by where it falls.
export function acwrColor(v: number | null): string {
  if (v === null) return "#3A3A42";
  if (v < 0.8) return "#FACC15"; // undertrained — amber
  if (v <= 1.3) return "#22C55E"; // safe — green
  if (v <= 1.5) return "#F97316"; // caution — orange
  return "#EF4444"; // danger — red
}

// Continuous green → amber → red ramp for 0..100 stress-like scales.
// t in [0,1]; 0 = calm (green), 1 = high (red).
export function stressRamp(t: number): string {
  const x = Math.min(1, Math.max(0, t));
  // green (#22C55E) → amber (#F59E0B) → red (#EF4444)
  const stops: [number, [number, number, number]][] = [
    [0, [0x22, 0xc5, 0x5e]],
    [0.5, [0xf5, 0x9e, 0x0b]],
    [1, [0xef, 0x44, 0x44]],
  ];
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (x >= stops[i][0] && x <= stops[i + 1][0]) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const span = hi[0] - lo[0] || 1;
  const k = (x - lo[0]) / span;
  const ch = (a: number, b: number) => Math.round(a + (b - a) * k);
  const r = ch(lo[1][0], hi[1][0]);
  const g = ch(lo[1][1], hi[1][1]);
  const b = ch(lo[1][2], hi[1][2]);
  return `rgb(${r}, ${g}, ${b})`;
}

// Three-phase ramp (red / orange / green) for a value within a domain. Used by
// the HRV phase bar: low = red (under-recovered), high = green (recovered).
export const PHASE_COLORS = ["#EF4444", "#F97316", "#22C55E"] as const;
