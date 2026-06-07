import { useState } from "react";
import { listCheckins, listMiniTests } from "../api/endpoints";
import type { CheckinOut, MiniTestOut } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { MetricChart, type MetricPoint } from "../components/MetricChart";
import { Spinner } from "../components/Spinner";
import { PageHeader, PillTabs } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";

interface HomeData {
  checkins: CheckinOut[];
  reaction: MiniTestOut[];
  jump: MiniTestOut[];
}

async function loadHome(days: number): Promise<HomeData> {
  const from = daysAgoISO(days);
  const to = todayISO();
  const [checkins, reaction, jump] = await Promise.all([
    listCheckins(from, to),
    listMiniTests(from, to, "reaction"),
    listMiniTests(from, to, "jump"),
  ]);
  return { checkins, reaction, jump };
}

const RANGES: { value: number; label: string }[] = [
  { value: 30, label: "30 j" },
  { value: 90, label: "90 j" },
  { value: 180, label: "180 j" },
];

// Onglet 1 — Accueil. The athlete's own inputs over time, in spec order:
// forme · fatigue · motivation · stress (à venir) · temps de réaction · saut.
export function HomePage() {
  const [days, setDays] = useState(90);
  const { data, error, loading, reload } = useAsync(() => loadHome(days), [days]);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader
        title="Accueil"
        subtitle="Tes ressentis et tes tests, jour après jour."
        action={<PillTabs value={days} onChange={setDays} options={RANGES} />}
      />

      {loading && <Spinner label="Chargement de tes courbes…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Charts data={data} />}
    </div>
  );
}

function Charts({ data }: { data: HomeData }) {
  const form: MetricPoint[] = data.checkins.map((c) => ({ date: c.date, value: c.form_vs_normal }));
  const fatigue: MetricPoint[] = data.checkins.map((c) => ({ date: c.date, value: c.fatigue }));
  const motivation: MetricPoint[] = data.checkins.map((c) => ({
    date: c.date,
    value: c.motivation,
  }));
  const stress: MetricPoint[] = data.checkins.map((c) => ({
    date: c.date,
    value: c.stress ?? null,
  }));
  const reaction: MetricPoint[] = data.reaction.map((t) => ({
    date: t.date,
    value: t.data.mean_rt_ms ?? null,
  }));
  const jump: MetricPoint[] = data.jump.map((t) => ({
    date: t.date,
    value: t.data.height_cm ?? null,
  }));

  return (
    <div className="flex flex-col gap-4">
      <MetricChart
        title="Forme"
        hint="Ton ressenti vs un jour normal · −2 à +2"
        points={form}
        zeroLine
      />
      <MetricChart title="Fatigue" hint="1 = frais · 5 = épuisé" points={fatigue} />
      <MetricChart
        title="Motivation"
        hint="Vs un jour normal · −2 à +2"
        points={motivation}
        zeroLine
      />
      <MetricChart
        title="Stress"
        hint="Vs un jour normal · −2 à +2 · saisi dans la routine"
        points={stress}
        zeroLine
      />

      <MetricChart
        title="Temps de réaction"
        hint="Plus bas = mieux"
        points={reaction}
        unit=" ms"
      />
      <MetricChart title="Saut" hint="Hauteur du CMJ · plus haut = mieux" points={jump} unit=" cm" />
    </div>
  );
}
