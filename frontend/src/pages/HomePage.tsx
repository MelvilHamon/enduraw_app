import { Link } from "react-router-dom";
import { listCheckins, listMiniTests } from "../api/endpoints";
import type { CheckinOut, MiniTestOut } from "../api/types";
import { CompareTriple } from "../components/charts/CompareTriple";
import { ErrorBanner } from "../components/ErrorBanner";
import { MetricCard } from "../components/MetricCard";
import { HeroSkeleton, ListSkeleton } from "../components/Skeleton";
import { Card, Chip, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { daysAgoISO, todayISO } from "../lib/date";
import { METRIC_COLOR } from "../lib/palette";
import { triple, valueOn, type DatedPoint } from "../lib/stats";

interface HomeData {
  checkins: CheckinOut[];
  reaction: MiniTestOut[];
  jump: MiniTestOut[];
}

// Wide window so the expandable detail charts have history to show.
const WINDOW_DAYS = 180;

async function loadHome(): Promise<HomeData> {
  const from = daysAgoISO(WINDOW_DAYS);
  const to = todayISO();
  const [checkins, reaction, jump] = await Promise.all([
    listCheckins(from, to),
    listMiniTests(from, to, "reaction"),
    listMiniTests(from, to, "jump"),
  ]);
  return { checkins, reaction, jump };
}

const byDate = (a: DatedPoint, b: DatedPoint) => a.date.localeCompare(b.date);

// Onglet 1 — Accueil. Each input is summarised as "today · yesterday · 7-day
// average"; tap a card to reveal its history curve.
export function HomePage() {
  const { data, error, loading, reload } = useAsync(loadHome, []);

  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader title="Accueil" subtitle="Aujourd'hui, hier et ta moyenne 7 jours." />

      {loading && (
        <div className="flex flex-col gap-4">
          <HeroSkeleton />
          <ListSkeleton count={4} />
        </div>
      )}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && <Cards data={data} />}
    </div>
  );
}

function Cards({ data }: { data: HomeData }) {
  const today = todayISO();
  const form = [...data.checkins.map((c) => ({ date: c.date, value: c.form_vs_normal }))].sort(byDate);
  const fatigue = [...data.checkins.map((c) => ({ date: c.date, value: c.fatigue }))].sort(byDate);
  const motivation = [...data.checkins.map((c) => ({ date: c.date, value: c.motivation }))].sort(byDate);
  const stress = [...data.checkins.map((c) => ({ date: c.date, value: c.stress ?? null }))].sort(byDate);
  const reaction = [...data.reaction.map((t) => ({ date: t.date, value: t.data.mean_rt_ms ?? null }))].sort(byDate);
  const jump = [...data.jump.map((t) => ({ date: t.date, value: t.data.height_cm ?? null }))].sort(byDate);

  // Today's check-in missing → prompt the routine on the subjective cards.
  const checkinDoneToday = form.some((p) => p.date === today && p.value !== null);

  return (
    <div className="flex flex-col gap-4">
      <TodayHero
        done={checkinDoneToday}
        form={valueOn(form, today)}
        fatigue={valueOn(fatigue, today)}
        motivation={valueOn(motivation, today)}
        stress={valueOn(stress, today)}
      />

      <SubjectiveCard
        title="Forme"
        hint="Ton ressenti vs un jour normal · −2 à +2"
        color={METRIC_COLOR.form}
        points={form}
        today={today}
        done={checkinDoneToday}
        signed
      />
      <SubjectiveCard
        title="Fatigue"
        hint="1 = frais · 5 = épuisé"
        color={METRIC_COLOR.fatigue}
        points={fatigue}
        today={today}
        done={checkinDoneToday}
      />
      <SubjectiveCard
        title="Motivation"
        hint="Vs un jour normal · −2 à +2"
        color={METRIC_COLOR.motivation}
        points={motivation}
        today={today}
        done={checkinDoneToday}
        signed
      />
      <SubjectiveCard
        title="Stress"
        hint="Vs un jour normal · −2 à +2"
        color={METRIC_COLOR.stress}
        points={stress}
        today={today}
        done={checkinDoneToday}
        signed
      />

      <MetricCard
        title="Temps de réaction"
        hint="Écart à ta moyenne 7 j · plus bas = mieux"
        color={METRIC_COLOR.reaction}
        points={reaction}
        today={today}
        unit=" ms"
        summary={tripleSummary(reaction, today, METRIC_COLOR.reaction, {
          unit: " ms",
          mode: "deviation",
          betterLower: true,
        })}
      />
      <MetricCard
        title="Saut"
        hint="Hauteur du CMJ · écart à ta moyenne 7 j"
        color={METRIC_COLOR.jump}
        points={jump}
        today={today}
        unit=" cm"
        decimals={1}
        summary={tripleSummary(jump, today, METRIC_COLOR.jump, {
          unit: " cm",
          decimals: 1,
          mode: "deviation",
        })}
      />
    </div>
  );
}

// Page hero — a snapshot of what you logged today (the screen's whole purpose:
// representing the data you enter from the app). Falls back to a routine prompt.
function TodayHero({
  done,
  form,
  fatigue,
  motivation,
  stress,
}: {
  done: boolean;
  form: number | null;
  fatigue: number | null;
  motivation: number | null;
  stress: number | null;
}) {
  if (!done) {
    return (
      <Link to="/routine" className="block">
        <Card className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-20 h-44 w-44 rounded-full bg-flame-500 opacity-20 blur-3xl"
          />
          <div className="relative flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-400">
                Ressenti du jour
              </p>
              <p className="mt-2 font-display text-2xl text-stone-50">Pas encore renseigné</p>
              <p className="mt-1 text-sm text-stone-400">Complète ta routine — 30 secondes.</p>
            </div>
            <span className="font-display text-2xl text-flame-500">→</span>
          </div>
        </Card>
      </Link>
    );
  }

  return (
    <Card className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-20 h-44 w-44 rounded-full bg-flame-500 opacity-20 blur-3xl"
      />
      <div className="relative">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-400">
          Ressenti du jour
        </p>
        <div className="mt-2 flex items-end gap-2">
          <span className="font-display nums text-[44px] leading-[0.9] text-stone-50">
            {form === null ? "—" : signed(form)}
          </span>
          <span className="mb-1 text-sm text-stone-400">forme vs normal</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip color="#D6D3D1">Fatigue {fatigue === null ? "—" : `${fatigue}/5`}</Chip>
          <Chip color="#D6D3D1">Motivation {motivation === null ? "—" : signed(motivation)}</Chip>
          <Chip color="#D6D3D1">Stress {stress === null ? "—" : signed(stress)}</Chip>
        </div>
      </div>
    </Card>
  );
}

const signed = (v: number) => (v > 0 ? `+${v}` : v < 0 ? `−${Math.abs(v)}` : "0");

function tripleSummary(
  points: DatedPoint[],
  today: string,
  color: string,
  opts: {
    unit?: string;
    decimals?: number;
    signed?: boolean;
    mode?: "value" | "deviation";
    betterLower?: boolean;
  } = {},
) {
  const t = triple(points, today);
  return (
    <CompareTriple
      today={t.today}
      yesterday={t.yesterday}
      mean7={t.mean7}
      color={color}
      unit={opts.unit}
      decimals={opts.decimals ?? 0}
      signed={opts.signed}
      mode={opts.mode}
      betterLower={opts.betterLower}
    />
  );
}

function SubjectiveCard({
  title,
  hint,
  color,
  points,
  today,
  done,
  signed = false,
}: {
  title: string;
  hint: string;
  color: string;
  points: DatedPoint[];
  today: string;
  done: boolean;
  signed?: boolean;
}) {
  const summary = done ? (
    tripleSummary(points, today, color, { signed })
  ) : (
    <RoutineCTA />
  );
  return (
    <MetricCard title={title} hint={hint} color={color} points={points} today={today} summary={summary} />
  );
}

function RoutineCTA() {
  return (
    <Link
      to="/routine"
      className="flex items-center justify-between gap-2 rounded-xl border border-dashed border-flame-700 bg-flame-900/10 px-3 py-3 text-sm"
    >
      <span className="text-stone-300">Complète le formulaire dans Routine</span>
      <span className="font-semibold text-flame-500">→</span>
    </Link>
  );
}
