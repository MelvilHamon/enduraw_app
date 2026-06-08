// Horizontal three-phase bar (red / orange / green) with a cursor placed at the
// 7-day average. Used for HRV: low RMSSD = under-recovered (red), high = well
// recovered (green). The domain is derived from the data so the bar adapts to
// the athlete's own range.

import { PHASE_COLORS } from "../../lib/palette";

interface PhaseBarProps {
  value: number | null; // 7-day average to mark
  min: number;
  max: number;
  unit?: string;
  decimals?: number;
  phaseLabels?: [string, string, string]; // low, mid, high
}

const W = 320;
const BAR_Y = 20;
const BAR_H = 14;
const X0 = 12;
const X1 = W - 12;

export function PhaseBar({
  value,
  min,
  max,
  unit = "",
  decimals = 0,
  phaseLabels = ["Sous-récupéré", "Modéré", "Bien récupéré"],
}: PhaseBarProps) {
  const span = max - min || 1;
  const x = (v: number) => X0 + ((Math.min(max, Math.max(min, v)) - min) / span) * (X1 - X0);
  const third = (X1 - X0) / 3;

  const phaseIndex = value === null ? null : Math.min(2, Math.max(0, Math.floor(((value - min) / span) * 3)));

  return (
    <div>
      <svg viewBox={`0 0 ${W} 52`} className="w-full" role="img">
        {/* three coloured segments */}
        {PHASE_COLORS.map((c, i) => (
          <rect
            key={c}
            x={X0 + third * i}
            y={BAR_Y}
            width={third}
            height={BAR_H}
            fill={c}
            opacity={phaseIndex === null || phaseIndex === i ? 0.95 : 0.35}
            rx={i === 0 ? 4 : i === 2 ? 4 : 0}
          />
        ))}

        {/* cursor at the 7-day average */}
        {value !== null && (
          <g>
            <polygon
              points={`${x(value)},${BAR_Y - 3} ${x(value) - 5},${BAR_Y - 11} ${x(value) + 5},${BAR_Y - 11}`}
              fill="#FFFFFF"
            />
            <line x1={x(value)} x2={x(value)} y1={BAR_Y - 2} y2={BAR_Y + BAR_H + 2} stroke="#FFFFFF" strokeWidth={2} />
            <text x={x(value)} y={BAR_Y + BAR_H + 16} textAnchor="middle" className="fill-stone-200" style={{ fontSize: 10, fontWeight: 700 }}>
              {Number(value.toFixed(decimals))}
              {unit}
            </text>
          </g>
        )}
      </svg>

      <div className="mt-0.5 flex justify-between px-1 text-[10px] text-stone-500">
        {phaseLabels.map((l, i) => (
          <span key={l} style={{ color: phaseIndex === i ? PHASE_COLORS[i] : undefined }}>
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}
