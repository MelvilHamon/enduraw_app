// Tiny descriptive-stats helpers for metric drill-downs. All ignore nulls.

export interface Stats {
  n: number;
  latest: number | null;
  mean: number | null;
  min: number | null;
  max: number | null;
}

export function summarize(values: (number | null)[]): Stats {
  const nums = values.filter((v): v is number => v !== null);
  if (nums.length === 0) return { n: 0, latest: null, mean: null, min: null, max: null };
  const sum = nums.reduce((a, b) => a + b, 0);
  return {
    n: nums.length,
    // Last non-null in chronological order.
    latest: nums[nums.length - 1],
    mean: sum / nums.length,
    min: Math.min(...nums),
    max: Math.max(...nums),
  };
}

// "432" minutes → "7 h 12".
export function formatDuration(min: number): string {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return `${h} h ${String(m).padStart(2, "0")}`;
}

// --- Date-aware helpers for "today · yesterday · 7-day average" cards --------

export interface DatedPoint {
  date: string; // YYYY-MM-DD
  value: number | null;
}

function isoMinusDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() - days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// Last non-null value recorded exactly on `date`, or null.
export function valueOn(points: DatedPoint[], date: string): number | null {
  let v: number | null = null;
  for (const p of points) if (p.date === date && p.value !== null) v = p.value;
  return v;
}

// Mean of non-null values in the `n`-day window ending at `end` (inclusive).
export function meanLastN(points: DatedPoint[], n: number, end: string): number | null {
  const from = isoMinusDays(end, n - 1);
  const nums = points
    .filter((p) => p.value !== null && p.date >= from && p.date <= end)
    .map((p) => p.value as number);
  if (nums.length === 0) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

export interface Triple {
  today: number | null;
  yesterday: number | null;
  mean7: number | null;
}

// The three numbers every Accueil/Charge summary card needs. `mean7` is the
// 7-day average up to and including yesterday — a stable reference the day's
// value can be read against.
export function triple(points: DatedPoint[], todayDate: string): Triple {
  const yDate = isoMinusDays(todayDate, 1);
  return {
    today: valueOn(points, todayDate),
    yesterday: valueOn(points, yDate),
    mean7: meanLastN(points, 7, yDate),
  };
}
