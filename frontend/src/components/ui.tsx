// Small shared layout primitives for the design system. Keep these dumb and
// composable — screens assemble them, they hold no data logic.

import type { ReactNode } from "react";

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
        <h1 className="text-2xl font-bold leading-tight text-stone-50">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-stone-400">{subtitle}</p>}
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
    <section className={`rounded-2xl border border-ink-600 bg-ink-800 p-4 ${className}`}>
      {children}
    </section>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-sm font-semibold text-stone-300">{children}</h2>;
}

// Compact pill segmented control (e.g. a 30/90/180-day range switcher).
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
    <div className="inline-flex rounded-full border border-ink-600 bg-ink-800 p-0.5 text-sm">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            onClick={() => onChange(o.value)}
            className={`rounded-full px-3 py-1 transition-colors ${
              active ? "bg-flame-500 font-semibold text-ink-950" : "text-stone-400 hover:text-stone-200"
            }`}
          >
            {o.label}
          </button>
        );
      })}
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
