// Vertical bar chart, one bar per week. Used for ACWR-by-week: each bar is
// coloured by its zone, with the 0.8–1.3 safe band shaded behind the bars.

export interface WeeklyBar {
  label: string; // e.g. "S-3"
  value: number | null;
  color: string;
}

interface WeeklyBarsProps {
  bars: WeeklyBar[];
  decimals?: number;
  // Optional shaded reference band (e.g. ACWR safe zone).
  band?: { from: number; to: number };
  // Force the y-domain top; otherwise derived from the data.
  maxValue?: number;
}

const H = 150;
const PAD_T = 16;
const PAD_B = 20;

export function WeeklyBars({ bars, decimals = 2, band, maxValue }: WeeklyBarsProps) {
  const vals = bars.map((b) => b.value).filter((v): v is number => v !== null);
  if (vals.length === 0) {
    return <p className="py-6 text-center text-sm text-stone-400">Pas assez de données.</p>;
  }
  const top = maxValue ?? Math.max(...vals, band?.to ?? 0) * 1.15;
  const plotH = H - PAD_T - PAD_B;
  const y = (v: number) => PAD_T + (1 - v / (top || 1)) * plotH;

  const n = bars.length;
  const W = 320;
  const slot = W / n;
  const barW = Math.min(34, slot * 0.5);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img">
      {/* safe band */}
      {band && (
        <rect x={0} y={y(band.to)} width={W} height={Math.max(0, y(band.from) - y(band.to))} fill="#22C55E" opacity={0.08} />
      )}
      {band && (
        <>
          <line x1={0} x2={W} y1={y(band.from)} y2={y(band.from)} stroke="#22C55E" strokeWidth={1} strokeDasharray="3 3" opacity={0.4} />
          <line x1={0} x2={W} y1={y(band.to)} y2={y(band.to)} stroke="#22C55E" strokeWidth={1} strokeDasharray="3 3" opacity={0.4} />
        </>
      )}

      {bars.map((b, i) => {
        const cx = slot * i + slot / 2;
        if (b.value === null) {
          return (
            <text key={i} x={cx} y={H - 6} textAnchor="middle" className="fill-stone-600" style={{ fontSize: 9 }}>
              {b.label}
            </text>
          );
        }
        const top0 = y(b.value);
        const h = H - PAD_B - top0;
        return (
          <g key={i}>
            <rect x={cx - barW / 2} y={top0} width={barW} height={Math.max(1, h)} rx={4} fill={b.color} />
            <text x={cx} y={top0 - 4} textAnchor="middle" style={{ fontSize: 10, fontWeight: 700, fill: b.color }}>
              {Number(b.value.toFixed(decimals))}
            </text>
            <text x={cx} y={H - 6} textAnchor="middle" className="fill-stone-500" style={{ fontSize: 9 }}>
              {b.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
