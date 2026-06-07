// Dependency-free multi-series SVG line chart with axes + scale. Each series
// shares the x-axis (dates); all series are auto-scaled onto a shared y-axis
// with "nice" rounded ticks, gridlines and date labels.

import { shortDate } from "../lib/date";

export interface ChartSeries {
  name: string;
  color: string;
  points: { date: string; value: number | null }[];
}

interface LineChartProps {
  series: ChartSeries[];
  height?: number;
  // Optional horizontal reference line (e.g. y=0 for divergence).
  zeroLine?: boolean;
  // Number of y-axis ticks (gridlines). Defaults to 4 intervals.
  yTicks?: number;
  // Optional unit suffix appended to y-axis labels (e.g. "ms", "%").
  unit?: string;
  // Optional custom y-value formatter (takes precedence over `unit`).
  formatValue?: (v: number) => string;
}

const WIDTH = 320;
const PAD_T = 10;
const PAD_R = 10;
const GUTTER_L = 34; // room for y-axis labels
const GUTTER_B = 18; // room for x-axis date labels

// Round a raw step up to a "nice" 1/2/5 × 10^n value so ticks land on
// human-friendly numbers.
function niceStep(raw: number): number {
  if (raw <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / pow;
  const nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return nice * pow;
}

export function LineChart({
  series,
  height = 160,
  zeroLine = false,
  yTicks = 4,
  unit,
  formatValue,
}: LineChartProps) {
  const allDates = Array.from(
    new Set(series.flatMap((s) => s.points.map((p) => p.date))),
  ).sort();
  const values = series.flatMap((s) =>
    s.points.map((p) => p.value).filter((v): v is number => v !== null),
  );

  if (allDates.length < 2 || values.length === 0) {
    return <p className="py-6 text-center text-sm text-stone-500">Pas assez de données.</p>;
  }

  const rawMin = Math.min(...values, zeroLine ? 0 : Infinity);
  const rawMax = Math.max(...values, zeroLine ? 0 : -Infinity);
  // Build nice tick bounds around the data range.
  const step = niceStep((rawMax - rawMin || 1) / yTicks);
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step;
  const span = max - min || 1;

  const plotW = WIDTH - GUTTER_L - PAD_R;
  const plotH = height - PAD_T - GUTTER_B;
  const xIndex = new Map(allDates.map((d, i) => [d, i]));

  const x = (date: string) =>
    GUTTER_L + ((xIndex.get(date) ?? 0) / (allDates.length - 1)) * plotW;
  const y = (value: number) => PAD_T + (1 - (value - min) / span) * plotH;

  const fmt = (v: number) =>
    formatValue ? formatValue(v) : `${Number(v.toFixed(2))}${unit ? unit : ""}`;

  const ticks: number[] = [];
  for (let v = min; v <= max + step / 2; v += step) ticks.push(Number(v.toFixed(6)));

  function pathFor(points: ChartSeries["points"]): string {
    let d = "";
    let pen = false;
    for (const p of points) {
      if (p.value === null) {
        pen = false;
        continue;
      }
      d += `${pen ? "L" : "M"}${x(p.date).toFixed(1)} ${y(p.value).toFixed(1)} `;
      pen = true;
    }
    return d.trim();
  }

  // X labels: first, middle, last (avoids crowding on long windows).
  const xLabelDates = [
    allDates[0],
    allDates[Math.floor((allDates.length - 1) / 2)],
    allDates[allDates.length - 1],
  ];

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" role="img">
        {/* gridlines + y labels */}
        {ticks.map((t) => {
          const yy = y(t);
          const isZero = zeroLine && Math.abs(t) < 1e-9;
          return (
            <g key={t}>
              <line
                x1={GUTTER_L}
                x2={WIDTH - PAD_R}
                y1={yy}
                y2={yy}
                stroke={isZero ? "#3A3A42" : "#1F1F23"}
                strokeWidth={1}
                strokeDasharray={isZero ? "3 3" : undefined}
              />
              <text
                x={GUTTER_L - 5}
                y={yy + 3}
                textAnchor="end"
                className="fill-stone-500"
                style={{ fontSize: 9 }}
              >
                {fmt(t)}
              </text>
            </g>
          );
        })}

        {/* series */}
        {series.map((s) => (
          <path
            key={s.name}
            d={pathFor(s.points)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* x labels */}
        {xLabelDates.map((d, i) => (
          <text
            key={`${d}-${i}`}
            x={Math.min(Math.max(x(d), GUTTER_L + 6), WIDTH - PAD_R - 6)}
            y={height - 5}
            textAnchor={i === 0 ? "start" : i === xLabelDates.length - 1 ? "end" : "middle"}
            className="fill-stone-500"
            style={{ fontSize: 9 }}
          >
            {shortDate(d)}
          </text>
        ))}
      </svg>

      {series.length > 1 && (
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-stone-400">
          {series.map((s) => (
            <span key={s.name} className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
