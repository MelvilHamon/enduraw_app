import { Link } from "react-router-dom";
import { Card, PageHeader } from "../components/ui";

// Profil → Paramètres. Connect data sources. The OAuth wiring is a later step;
// for now each source is listed with its kind and a disabled connect action.
type Source = { name: string; kind: string };

const WATCHES: Source[] = [
  { name: "Garmin", kind: "Montre" },
  { name: "Coros", kind: "Montre" },
];
const PLATFORMS: Source[] = [
  { name: "PacePilot", kind: "Plateforme" },
  { name: "Strava", kind: "Plateforme" },
];

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-5 py-2">
      <PageHeader
        title="Paramètres"
        subtitle="Connecte tes sources de données."
        action={
          <Link to="/profile" className="text-sm text-stone-400 hover:text-flame-500">
            ← Profil
          </Link>
        }
      />

      <Section title="Montre" sources={WATCHES} />
      <Section title="Plateformes" sources={PLATFORMS} />
    </div>
  );
}

function Section({ title, sources }: { title: string; sources: Source[] }) {
  return (
    <Card>
      <h2 className="text-sm font-semibold text-stone-300">{title}</h2>
      <ul className="mt-3 flex flex-col divide-y divide-ink-600">
        {sources.map((s) => (
          <li key={s.name} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
            <div>
              <p className="text-sm font-medium text-stone-100">{s.name}</p>
              <p className="text-xs text-stone-500">{s.kind}</p>
            </div>
            <button
              type="button"
              disabled
              className="rounded-full border border-ink-600 px-3 py-1 text-xs text-stone-500"
            >
              Bientôt
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
