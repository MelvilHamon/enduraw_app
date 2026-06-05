// Minimal hand-rolled multi-series SVG line chart — no charting dependency, in
// keeping with the deliberately-brut draft. Each series shares the x-axis (dates)
// and is auto-scaled across all series on a shared y-axis.

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
}

const WIDTH = 320;
const PAD = 8;

export function LineChart({ series, height = 140, zeroLine = false }: LineChartProps) {
  const allDates = Array.from(
    new Set(series.flatMap((s) => s.points.map((p) => p.date))),
  ).sort();
  const values = series.flatMap((s) =>
    s.points.map((p) => p.value).filter((v): v is number => v !== null),
  );

  if (allDates.length < 2 || values.length === 0) {
    return <p className="py-6 text-center text-sm text-slate-500">Pas assez de données.</p>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const xIndex = new Map(allDates.map((d, i) => [d, i]));

  const x = (date: string) =>
    PAD + ((xIndex.get(date) ?? 0) / (allDates.length - 1)) * (WIDTH - 2 * PAD);
  const y = (value: number) => PAD + (1 - (value - min) / span) * (height - 2 * PAD);

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

  const zeroY = zeroLine && min <= 0 && max >= 0 ? y(0) : null;

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" role="img">
        {zeroY !== null && (
          <line
            x1={PAD}
            x2={WIDTH - PAD}
            y1={zeroY}
            y2={zeroY}
            stroke="#475569"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        )}
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
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-400">
        {series.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}
