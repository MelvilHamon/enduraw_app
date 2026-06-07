export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-stone-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink-600 border-t-flame-500" />
      {label && <p className="text-sm">{label}</p>}
    </div>
  );
}
