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
