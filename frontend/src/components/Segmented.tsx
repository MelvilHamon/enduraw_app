interface Option {
  value: number;
  label: string;
  sub?: string;
}

interface SegmentedProps {
  title: string;
  hint?: string;
  options: Option[];
  value: number | null;
  onChange: (value: number) => void;
}

/** Big-target segmented selector for the 3-tap check-in. */
export function Segmented({ title, hint, options, value, onChange }: SegmentedProps) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-base font-semibold text-slate-100">{title}</legend>
      {hint && <p className="-mt-1 text-xs text-slate-400">{hint}</p>}
      <div className="flex gap-2">
        {options.map((opt) => {
          const active = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              className={`flex flex-1 flex-col items-center gap-0.5 rounded-xl border px-1 py-3 text-center ${
                active
                  ? "border-slate-100 bg-slate-100 text-slate-900"
                  : "border-slate-700 bg-slate-900 text-slate-300"
              }`}
            >
              <span className="text-lg font-bold leading-none">{opt.label}</span>
              {opt.sub && (
                <span className={`text-[10px] ${active ? "text-slate-600" : "text-slate-500"}`}>
                  {opt.sub}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
