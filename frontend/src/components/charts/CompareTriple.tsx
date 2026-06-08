// Compact "today · yesterday · 7-day average" summary. A horizontal track shows
// where today and yesterday sit relative to the 7-day average (a notch); below,
// three figures spell it out. Two modes:
//   "value"     — plots the raw values, reference notch at the 7-day mean.
//   "deviation" — plots the gap to the 7-day mean (centre = 0), figures show ±.

export interface CompareTripleProps {
  today: number | null;
  yesterday: number | null;
  mean7: number | null;
  color: string;
  unit?: string;
  decimals?: number;
  mode?: "value" | "deviation";
  signed?: boolean; // signed scale (-2..+2): always print a leading +
  betterLower?: boolean; // lower is better (reaction time) → flips delta colours
}

const W = 320;
const TRACK_Y = 26;
const X0 = 18;
const X1 = W - 18;

function fmtNum(v: number, decimals: number): string {
  return `${Number(v.toFixed(decimals))}`;
}

export function CompareTriple({
  today,
  yesterday,
  mean7,
  color,
  unit = "",
  decimals = 0,
  mode = "value",
  signed = false,
  betterLower = false,
}: CompareTripleProps) {
  const deviation = mode === "deviation";

  // Plotted positions (what we lay on the track).
  const ref = deviation ? 0 : (mean7 ?? null);
  const plotToday = deviation && today !== null && mean7 !== null ? today - mean7 : today;
  const plotYest = deviation && yesterday !== null && mean7 !== null ? yesterday - mean7 : yesterday;

  const plotted = [plotToday, plotYest, ref].filter((v): v is number => v !== null);
  let lo = Math.min(...plotted);
  let hi = Math.max(...plotted);
  if (deviation) {
    const m = Math.max(Math.abs(lo), Math.abs(hi), unit === " ms" ? 5 : 0.5);
    lo = -m;
    hi = m;
  } else {
    const pad = (hi - lo || Math.abs(hi) || 1) * 0.25;
    lo -= pad;
    hi += pad;
  }
  const span = hi - lo || 1;
  const x = (v: number) => X0 + ((v - lo) / span) * (X1 - X0);

  const sign = (v: number) => (v > 0 ? `+${fmtNum(v, decimals)}` : fmtNum(v, decimals));
  const printVal = (v: number | null) =>
    v === null ? "—" : signed ? `${sign(v)}` : `${fmtNum(v, decimals)}`;

  // Delta good/bad colour for the headline figure.
  function deltaColor(): string {
    if (today === null || mean7 === null) return color;
    const d = today - mean7;
    if (Math.abs(d) < (decimals > 0 ? 0.05 : 0.5)) return "#9CA3AF";
    const up = d > 0;
    const good = betterLower ? !up : up;
    return good ? "#22C55E" : "#F43F5E";
  }

  const headline = deviation
    ? today !== null && mean7 !== null
      ? sign(today - mean7)
      : "—"
    : printVal(today);
  const headlineColor = deviation ? deltaColor() : color;

  return (
    <div>
      <svg viewBox={`0 0 ${W} 48`} className="w-full" role="img">
        {/* base track */}
        <line x1={X0} x2={X1} y1={TRACK_Y} y2={TRACK_Y} stroke="#2A2A30" strokeWidth={4} strokeLinecap="round" />

        {/* reference notch (7-day mean / zero) */}
        {ref !== null && (
          <g>
            <line x1={x(ref)} x2={x(ref)} y1={TRACK_Y - 8} y2={TRACK_Y + 8} stroke="#6B7280" strokeWidth={1.5} />
            <text x={x(ref)} y={TRACK_Y + 18} textAnchor="middle" className="fill-stone-500" style={{ fontSize: 8 }}>
              {deviation ? "moy 7 j" : "7 j"}
            </text>
          </g>
        )}

        {/* yesterday — hollow muted dot */}
        {plotYest !== null && (
          <circle cx={x(plotYest)} cy={TRACK_Y} r={4} fill="#161618" stroke="#6B7280" strokeWidth={2} />
        )}

        {/* today — filled glowing dot + floating value */}
        {plotToday !== null && (
          <g>
            <circle cx={x(plotToday)} cy={TRACK_Y} r={9} fill={color} opacity={0.18} />
            <circle cx={x(plotToday)} cy={TRACK_Y} r={5} fill={color} stroke="#0B0B0C" strokeWidth={1.5} />
            <text
              x={Math.min(Math.max(x(plotToday), X0 + 12), X1 - 12)}
              y={TRACK_Y - 11}
              textAnchor="middle"
              style={{ fontSize: 10, fontWeight: 700, fill: color }}
            >
              {headline}
              {unit}
            </text>
          </g>
        )}
      </svg>

      {/* three figures */}
      <div className="mt-1 grid grid-cols-3 gap-2 text-center">
        <Figure label="Aujourd'hui" value={headline === "—" ? "—" : `${headline}${unit}`} color={headlineColor} big />
        <Figure
          label="Hier"
          value={
            deviation
              ? yesterday !== null && mean7 !== null
                ? `${sign(yesterday - mean7)}${unit}`
                : "—"
              : yesterday === null
                ? "—"
                : `${printVal(yesterday)}${unit}`
          }
          color="#D6D3D1"
        />
        <Figure
          label="Moy 7 j"
          value={mean7 === null ? "—" : `${fmtNum(mean7, decimals)}${unit}`}
          color="#A8A29E"
        />
      </div>
    </div>
  );
}

function Figure({ label, value, color, big = false }: { label: string; value: string; color: string; big?: boolean }) {
  return (
    <div>
      <div className={`nums ${big ? "font-display text-2xl" : "font-semibold text-base"}`} style={{ color }}>
        {value}
      </div>
      <div className="mt-0.5 text-[10px] uppercase tracking-wide text-stone-400">{label}</div>
    </div>
  );
}
