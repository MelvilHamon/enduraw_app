// Detail curve shown when a metric card is expanded. Unlike the bare LineChart,
// this draws a soft gradient area under the line, a dashed period-average line
// across the whole chart, and a dashed 7-day-average line — so the reader sees
// the trend AND the two references at a glance.

import { useId } from "react";
import { shortDate } from "../../lib/date";

export interface AreaPoint {
  date: string;
  value: number | null;
}

interface AreaChartProps {
  points: AreaPoint[];
  color: string;
  height?: number;
  unit?: string;
  decimals?: number;
  // Reference lines.
  mean?: number | null; // period average (dashed, muted)
  mean7?: number | null; // 7-day average (dashed, accent)
}

const WIDTH = 320;
const PAD_T = 12;
const PAD_R = 12;
const GUTTER_L = 34;
const GUTTER_B = 18;

function niceStep(raw: number): number {
  if (raw <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / pow;
  const nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return nice * pow;
}

export function AreaChart({
  points,
  color,
  height = 180,
  unit,
  decimals = 0,
  mean = null,
  mean7 = null,
}: AreaChartProps) {
  const gid = useId();
  const dates = points.map((p) => p.date);
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);

  if (dates.length < 2 || values.length === 0) {
    return <p className="py-6 text-center text-sm text-stone-400">Pas assez de données.</p>;
  }

  const refs = [mean, mean7].filter((v): v is number => v !== null && v !== undefined);
  const rawMin = Math.min(...values, ...refs);
  const rawMax = Math.max(...values, ...refs);
  const step = niceStep((rawMax - rawMin || 1) / 4);
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step;
  const span = max - min || 1;

  const plotW = WIDTH - GUTTER_L - PAD_R;
  const plotH = height - PAD_T - GUTTER_B;
  const idx = new Map(dates.map((d, i) => [d, i]));
  const x = (date: string) => GUTTER_L + ((idx.get(date) ?? 0) / (dates.length - 1)) * plotW;
  const y = (v: number) => PAD_T + (1 - (v - min) / span) * plotH;
  const baseY = PAD_T + plotH;

  const fmt = (v: number) => `${Number(v.toFixed(decimals))}${unit ?? ""}`;

  // Line + area paths (lifting the pen across null gaps).
  let line = "";
  let area = "";
  let penDate: string | null = null;
  for (const p of points) {
    if (p.value === null) {
      if (penDate !== null) area += `L${x(penDate).toFixed(1)} ${baseY.toFixed(1)} Z `;
      penDate = null;
      continue;
    }
    const px = x(p.date).toFixed(1);
    const py = y(p.value).toFixed(1);
    if (penDate === null) {
      line += `M${px} ${py} `;
      area += `M${px} ${baseY.toFixed(1)} L${px} ${py} `;
    } else {
      line += `L${px} ${py} `;
      area += `L${px} ${py} `;
    }
    penDate = p.date;
  }
  if (penDate !== null) area += `L${x(penDate).toFixed(1)} ${baseY.toFixed(1)} Z `;

  const ticks: number[] = [];
  for (let v = min; v <= max + step / 2; v += step) ticks.push(Number(v.toFixed(6)));

  const xLabels = [dates[0], dates[Math.floor((dates.length - 1) / 2)], dates[dates.length - 1]];
  const last = [...points].reverse().find((p) => p.value !== null);

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" role="img">
        <defs>
          <linearGradient id={`area-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        {/* y gridlines + labels */}
        {ticks.map((t) => {
          const yy = y(t);
          return (
            <g key={t}>
              <line x1={GUTTER_L} x2={WIDTH - PAD_R} y1={yy} y2={yy} stroke="#1F1F23" strokeWidth={1} />
              <text x={GUTTER_L - 5} y={yy + 3} textAnchor="end" className="fill-stone-500" style={{ fontSize: 9 }}>
                {fmt(t)}
              </text>
            </g>
          );
        })}

        {/* gradient area + line */}
        <path d={area.trim()} fill={`url(#area-${gid})`} stroke="none" />
        <path d={line.trim()} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {/* period-average reference (muted dashed) */}
        {mean !== null && mean !== undefined && (
          <g>
            <line x1={GUTTER_L} x2={WIDTH - PAD_R} y1={y(mean)} y2={y(mean)} stroke="#6B7280" strokeWidth={1} strokeDasharray="4 3" />
            <text x={WIDTH - PAD_R} y={y(mean) - 3} textAnchor="end" className="fill-stone-400" style={{ fontSize: 8 }}>
              moy
            </text>
          </g>
        )}

        {/* 7-day-average reference (accent dashed) */}
        {mean7 !== null && mean7 !== undefined && (
          <g>
            <line x1={GUTTER_L} x2={WIDTH - PAD_R} y1={y(mean7)} y2={y(mean7)} stroke={color} strokeWidth={1} strokeDasharray="2 3" opacity={0.8} />
            <text x={WIDTH - PAD_R} y={y(mean7) + 8} textAnchor="end" style={{ fontSize: 8, fill: color }}>
              7 j
            </text>
          </g>
        )}

        {/* last-point dot */}
        {last && last.value !== null && (
          <circle cx={x(last.date)} cy={y(last.value)} r={3} fill={color} stroke="#0B0B0C" strokeWidth={1.5} />
        )}

        {/* x labels */}
        {xLabels.map((d, i) => (
          <text
            key={`${d}-${i}`}
            x={Math.min(Math.max(x(d), GUTTER_L + 6), WIDTH - PAD_R - 6)}
            y={height - 5}
            textAnchor={i === 0 ? "start" : i === xLabels.length - 1 ? "end" : "middle"}
            className="fill-stone-500"
            style={{ fontSize: 9 }}
          >
            {shortDate(d)}
          </text>
        ))}
      </svg>
    </div>
  );
}
