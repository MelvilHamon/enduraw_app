import { useState } from "react";
import { getTimeseries, listDailyMetrics } from "../api/endpoints";
import type { DailyMetricOut, Timeseries } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { MetricChart, type MetricPoint } from "../components/MetricChart";
import { Spinner } from "../components/Spinner";
import { PageHeader, PillTabs } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";

interface LoadData {
  ts: Timeseries;
  daily: DailyMetricOut[];
}

async function loadCharge(days: number): Promise<LoadData> {
  const from = daysAgoISO(days);
  const to = todayISO();
  const [ts, daily] = await Promise.all([
    getTimeseries(from, to, ["form", "acwr"]),
    listDailyMetrics(from, to),
  ]);
  return { ts, daily };
}

const RANGES: { value: number; label: string }[] = [
  { value: 30, label: "30 j" },
  { value: 90, label: "90 j" },
  { value: 180, label: "180 j" },
];

// Onglet 2 — Charge. Running training-load data: forme (Banister), ACWR, VO2.
export function LoadPage() {
  const [days, setDays] = useState(90);
  const { data, error, loading, reload } = useAsync(() => loadCharge(days), [days]);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader
        title="Charge"
        subtitle="Ta charge d'entraînement course à pied."
        action={<PillTabs value={days} onChange={setDays} options={RANGES} />}
      />

      {loading && <Spinner label="Chargement de ta charge…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Charts data={data} />}
    </div>
  );
}

function Charts({ data }: { data: LoadData }) {
  const form: MetricPoint[] = data.ts.series.form ?? [];
  const acwr: MetricPoint[] = data.ts.series.acwr ?? [];
  const vo2: MetricPoint[] = data.daily
    .filter((d) => d.vo2max !== null)
    .map((d) => ({ date: d.date, value: d.vo2max }));

  return (
    <div className="flex flex-col gap-4">
      <MetricChart
        title="Forme (calculée)"
        hint="Modèle Banister · positif = frais, négatif = chargé"
        points={form}
        decimals={1}
        zeroLine
      />
      <MetricChart
        title="ACWR"
        hint="Charge aiguë / chronique · zone sûre 0,8–1,3"
        points={acwr}
        decimals={2}
      />
      <MetricChart
        title="VO2 (estimé)"
        hint="Estimation montre · plus haut = mieux"
        points={vo2}
        unit=" ml/kg/min"
        decimals={1}
      />
    </div>
  );
}
