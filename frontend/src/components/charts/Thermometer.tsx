// Vertical "thermometer" gauge for the day's stress average. Calm at the bottom
// (green), high at the top (red); the mercury fills to the value and a marker
// pins the exact level. A single day figure — no time series.

import { stressRamp } from "../../lib/palette";

interface ThermometerProps {
  value: number | null; // 0..max
  max?: number;
  caption?: string;
}

const H = 180;
const TUBE_X = 70;
const TUBE_W = 22;
const TUBE_TOP = 16;
const TUBE_BOT = H - 36;
const BULB_R = 18;

export function Thermometer({ value, max = 100, caption }: ThermometerProps) {
  const frac = value === null ? 0 : Math.min(1, Math.max(0, value / max));
  const fillTop = TUBE_BOT - frac * (TUBE_BOT - TUBE_TOP);
  const color = stressRamp(frac);
  const bulbY = TUBE_BOT + 6;

  return (
    <div className="flex items-center gap-4">
      <svg viewBox={`0 0 140 ${H}`} className="h-44" role="img">
        <defs>
          <linearGradient id="thermo-scale" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#22C55E" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#EF4444" />
          </linearGradient>
        </defs>

        {/* glass tube */}
        <rect x={TUBE_X} y={TUBE_TOP} width={TUBE_W} height={TUBE_BOT - TUBE_TOP} rx={TUBE_W / 2} fill="#1F1F23" />
        {/* faint full-scale tint */}
        <rect x={TUBE_X + 5} y={TUBE_TOP} width={TUBE_W - 10} height={TUBE_BOT - TUBE_TOP} rx={(TUBE_W - 10) / 2} fill="url(#thermo-scale)" opacity={0.15} />

        {/* mercury */}
        <rect x={TUBE_X + 3} y={fillTop} width={TUBE_W - 6} height={TUBE_BOT - fillTop} rx={(TUBE_W - 6) / 2} fill={color} />
        <rect x={TUBE_X + 3} y={bulbY - BULB_R} width={TUBE_W - 6} height={BULB_R} fill={color} />
        {/* bulb */}
        <circle cx={TUBE_X + TUBE_W / 2} cy={bulbY} r={BULB_R} fill={color} />

        {/* level marker + value */}
        {value !== null && (
          <g>
            <line x1={TUBE_X - 8} x2={TUBE_X} y1={fillTop} y2={fillTop} stroke={color} strokeWidth={2} />
            <text x={TUBE_X - 12} y={fillTop + 4} textAnchor="end" style={{ fontSize: 16, fontWeight: 800, fill: color }}>
              {Math.round(value)}
            </text>
          </g>
        )}

        {/* scale ticks */}
        {[0, 25, 50, 75, 100].map((t) => {
          const ty = TUBE_BOT - (t / 100) * (TUBE_BOT - TUBE_TOP);
          return (
            <g key={t}>
              <line x1={TUBE_X + TUBE_W} x2={TUBE_X + TUBE_W + 5} y1={ty} y2={ty} stroke="#3A3A42" strokeWidth={1} />
              <text x={TUBE_X + TUBE_W + 8} y={ty + 3} className="fill-stone-600" style={{ fontSize: 8 }}>
                {t}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="text-sm text-stone-400">
        <div className="font-semibold text-stone-200">Stress du jour</div>
        {caption && <div className="mt-1 text-xs text-stone-500">{caption}</div>}
      </div>
    </div>
  );
}
