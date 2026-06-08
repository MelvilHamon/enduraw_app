// Small shared layout primitives for the design system. Keep these dumb and
// composable — screens assemble them, they hold no data logic.

import type { ReactNode } from "react";
import { ACCENT } from "../lib/palette";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <h1 className="font-display text-[26px] leading-none text-stone-50">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-stone-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-ink-700 bg-ink-800 p-4 shadow-card ${className}`}
    >
      {children}
    </section>
  );
}

// Quiet uppercase section label — reads like a TrainingPeaks/Linear field title.
export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-400">
      {children}
    </h2>
  );
}

// Page focal point: a big display value that states what the screen is about.
// `value` is the headline (number/word), `aside` an optional visual on the right,
// `children` optional chips/recap below the value row.
export function Hero({
  label,
  value,
  unit,
  caption,
  accent = ACCENT,
  aside,
  children,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  caption?: ReactNode;
  accent?: string;
  aside?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <Card className="relative overflow-hidden">
      {/* soft accent bloom in the corner — atmosphere without a coloured box */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-20 h-44 w-44 rounded-full opacity-20 blur-3xl"
        style={{ background: accent }}
      />
      <div className="relative flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-400">
            {label}
          </p>
          <div className="mt-2 flex items-end gap-2">
            <span className="font-display nums text-[44px] leading-[0.9] text-stone-50">
              {value}
            </span>
            {unit && <span className="mb-1 text-sm text-stone-400">{unit}</span>}
          </div>
          {caption && <div className="mt-2 text-sm text-stone-300">{caption}</div>}
          {children}
        </div>
        {aside && <div className="shrink-0">{aside}</div>}
      </div>
    </Card>
  );
}

// Small coloured chip, e.g. a delta or a status word.
export function Chip({
  children,
  color = ACCENT,
}: {
  children: ReactNode;
  color?: string;
}) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold nums"
      style={{ color, background: `${color}1f` }}
    >
      {children}
    </span>
  );
}

// Compact pill segmented control (e.g. a 7/30-day range switcher).
export function PillTabs<T extends string | number>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex rounded-full border border-ink-600 bg-ink-900 p-0.5 text-sm">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            onClick={() => onChange(o.value)}
            className={`rounded-full px-3 py-1 transition-colors ${
              active
                ? "bg-flame-500 font-semibold text-ink-950"
                : "text-stone-400 hover:text-stone-200"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

// Neutral empty state — an icon, a short title and a hint. Honest and calm,
// never a bare line of grey text.
export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-ink-600 px-6 py-10 text-center">
      {icon && (
        <div className="flex h-11 w-11 items-center justify-center rounded-full border border-ink-600 bg-ink-800 text-stone-400">
          {icon}
        </div>
      )}
      <div>
        <p className="text-sm font-semibold text-stone-200">{title}</p>
        {hint && <p className="mt-1 text-sm text-stone-400">{hint}</p>}
      </div>
      {action}
    </div>
  );
}

// Placeholder shown on tabs whose data wiring lands in a later phase. Honest
// about what's coming rather than faking content.
export function PhasePlaceholder({
  phase,
  items,
}: {
  phase: string;
  items: string[];
}) {
  return (
    <Card className="border-dashed">
      <p className="text-xs font-semibold uppercase tracking-wide text-flame-500">{phase}</p>
      <p className="mt-2 text-sm text-stone-300">Cet onglet arrive bientôt. Au programme :</p>
      <ul className="mt-3 space-y-1.5 text-sm text-stone-400">
        {items.map((it) => (
          <li key={it} className="flex gap-2">
            <span className="text-flame-500">•</span>
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
