// Circular gauges, hand-rolled in SVG. Three flavours so each metric reads
// differently:
//   SegmentedGauge — open-bottom 270° ring split into coloured bands (VO2 max,
//                    Garmin-style red→orange→green→blue→violet) with a marker.
//   ArcGauge       — open-bottom ring, single two-tone progress (orange fill +
//                    grey rest), big number in the hollow (body battery).
//   RingGauge      — full closed ring filled to a score, alarm-clock hands in
//                    the centre, score printed below (sleep score).

import type { GaugeSegment } from "../../lib/palette";

const SIZE = 180;
const CX = SIZE / 2;
const CY = SIZE / 2;

// Screen-space polar point: 0°=right, 90°=bottom, 180°=left, 270°=top (y-down).
function polar(r: number, deg: number): [number, number] {
  const a = (deg * Math.PI) / 180;
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
}

// Arc path from a0 to a1 (degrees), clockwise (increasing angle).
function arcPath(r: number, a0: number, a1: number): string {
  const [x0, y0] = polar(r, a0);
  const [x1, y1] = polar(r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

// Open-bottom geometry: 270° arc, gap centred on the bottom (90°).
const OPEN_START = 135;
const OPEN_SWEEP = 270;
const openAngle = (frac: number) => OPEN_START + Math.min(1, Math.max(0, frac)) * OPEN_SWEEP;

interface SegmentedGaugeProps {
  value: number | null;
  min: number;
  max: number;
  segments: GaugeSegment[];
  centerLabel: string;
  sublabel?: string;
  // Optional small delta chip under the value (e.g. "+0.2" over 7 days).
  delta?: number | null;
  deltaDecimals?: number;
}

export function SegmentedGauge({
  value,
  min,
  max,
  segments,
  centerLabel,
  sublabel,
  delta = null,
  deltaDecimals = 1,
}: SegmentedGaugeProps) {
  const frac = (v: number) => (v - min) / (max - min || 1);
  const markerFrac = value === null ? null : frac(value);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-44" role="img">
        {/* faint full track */}
        <path d={arcPath(74, OPEN_START, OPEN_START + OPEN_SWEEP)} fill="none" stroke="#1F1F23" strokeWidth={12} strokeLinecap="round" />
        {/* coloured bands */}
        {segments.map((s) => (
          <path
            key={`${s.from}-${s.to}`}
            d={arcPath(74, openAngle(frac(Math.max(s.from, min))), openAngle(frac(Math.min(s.to, max))))}
            fill="none"
            stroke={s.color}
            strokeWidth={12}
            strokeLinecap="butt"
          />
        ))}
        {/* value marker */}
        {markerFrac !== null && (
          <g>
            {(() => {
              const [mx, my] = polar(74, openAngle(markerFrac));
              return <circle cx={mx} cy={my} r={7} fill="#0B0B0C" stroke="#FFFFFF" strokeWidth={3} />;
            })()}
          </g>
        )}
        {/* centre label */}
        <text x={CX} y={CY - 2} textAnchor="middle" className="fill-stone-50 font-display nums" style={{ fontSize: 36 }}>
          {centerLabel}
        </text>
        {sublabel && (
          <text x={CX} y={CY + 18} textAnchor="middle" className="fill-stone-400" style={{ fontSize: 11 }}>
            {sublabel}
          </text>
        )}
      </svg>
      {delta !== null && delta !== undefined && (
        <span
          className="-mt-3 rounded-full px-2 py-0.5 text-xs font-semibold"
          style={{
            color: delta >= 0 ? "#22C55E" : "#F43F5E",
            background: delta >= 0 ? "rgba(34,197,94,0.12)" : "rgba(244,63,94,0.12)",
          }}
        >
          {delta >= 0 ? "+" : ""}
          {Number(delta.toFixed(deltaDecimals))} sur 7 j
        </span>
      )}
    </div>
  );
}

interface ArcGaugeProps {
  value: number | null;
  min?: number;
  max?: number;
  color?: string;
  label?: string; // small caption under the number
}

export function ArcGauge({ value, min = 0, max = 100, color = "#F97316", label }: ArcGaugeProps) {
  const frac = value === null ? 0 : Math.min(1, Math.max(0, (value - min) / (max - min || 1)));
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-44" role="img">
      {/* grey rest */}
      <path d={arcPath(74, OPEN_START, OPEN_START + OPEN_SWEEP)} fill="none" stroke="#2A2A30" strokeWidth={14} strokeLinecap="round" />
      {/* coloured fill */}
      {frac > 0 && (
        <path d={arcPath(74, OPEN_START, openAngle(frac))} fill="none" stroke={color} strokeWidth={14} strokeLinecap="round" />
      )}
      <text x={CX} y={CY + 4} textAnchor="middle" className="fill-stone-50 font-display nums" style={{ fontSize: 42 }}>
        {value === null ? "—" : Math.round(value)}
      </text>
      {label && (
        <text x={CX} y={CY + 26} textAnchor="middle" className="fill-stone-400" style={{ fontSize: 11 }}>
          {label}
        </text>
      )}
    </svg>
  );
}

interface RingGaugeProps {
  value: number | null; // 0..max
  max?: number;
  color?: string;
  scoreLabel?: string; // text printed below the ring
}

export function RingGauge({ value, max = 100, color = "#818CF8", scoreLabel }: RingGaugeProps) {
  const frac = value === null ? 0 : Math.min(0.9999, Math.max(0, value / max));
  // Full ring starts at the top (270°), sweeps clockwise.
  const start = 270;
  const end = 270 + 360 * frac;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-40" role="img">
        {/* full grey track */}
        <circle cx={CX} cy={CY} r={70} fill="none" stroke="#1F1F23" strokeWidth={12} />
        {/* progress */}
        {frac > 0 && (
          <path d={arcPath(70, start, end)} fill="none" stroke={color} strokeWidth={12} strokeLinecap="round" />
        )}
        {/* alarm-clock face in the middle */}
        <circle cx={CX} cy={CY} r={42} fill="#101012" stroke="#2A2A30" strokeWidth={1.5} />
        {/* clock ticks */}
        {[0, 90, 180, 270].map((a) => {
          const [x1, y1] = polar(38, a);
          const [x2, y2] = polar(32, a);
          return <line key={a} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#6B7280" strokeWidth={2} strokeLinecap="round" />;
        })}
        {/* hour + minute hands (~10:08, classic clock pose) */}
        {(() => {
          const [hx, hy] = polar(22, 270 - 60); // hour hand
          const [mx, my] = polar(32, 270 + 48); // minute hand
          return (
            <>
              <line x1={CX} y1={CY} x2={hx} y2={hy} stroke={color} strokeWidth={3} strokeLinecap="round" />
              <line x1={CX} y1={CY} x2={mx} y2={my} stroke="#E7E5E4" strokeWidth={2.5} strokeLinecap="round" />
              <circle cx={CX} cy={CY} r={3} fill="#E7E5E4" />
            </>
          );
        })()}
      </svg>
      <div className="mt-1 text-center">
        <span className="font-display nums text-2xl text-stone-50">{value === null ? "—" : Math.round(value)}</span>
        <span className="ml-1 text-xs text-stone-400">/ {max}</span>
        {scoreLabel && <div className="text-[11px] text-stone-400">{scoreLabel}</div>}
      </div>
    </div>
  );
}
