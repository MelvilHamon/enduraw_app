// Loading skeletons — shimmer placeholders shaped like the real content, so the
// layout doesn't jump when data arrives. Calmer and more premium than a spinner.

// A single shimmering block. `className` controls size / radius.
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden rounded-md bg-ink-700 ${className}`}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
    </div>
  );
}

// One card-shaped skeleton: a title line, a chunky visual block, a footer line.
export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-4 shadow-card">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-20 w-full" />
      <Skeleton className="mt-3 h-3 w-2/3" />
    </div>
  );
}

// A stack of card skeletons for a list-style screen (Accueil/Charge/Santé).
export function ListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

// A hero-shaped skeleton for the focal point at the top of a screen.
export function HeroSkeleton() {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-4 shadow-card">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-10 w-32" />
      <Skeleton className="mt-3 h-3 w-48" />
    </div>
  );
}
