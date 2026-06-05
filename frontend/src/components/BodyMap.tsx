import { useState } from "react";
import type { BodyRegion, Side } from "../api/types";
import { REGION_LABEL } from "../lib/labels";

export interface BodyZone {
  region: BodyRegion;
  side: Side;
  cx: number;
  cy: number;
}

// Flat, runner-focused zone map (no anatomical peel — that's step 12). Coordinates
// are on a 200×420 viewBox silhouette. Side is encoded per marker.
const FRONT_ZONES: BodyZone[] = [
  { region: "neck", side: "center", cx: 100, cy: 70 },
  { region: "shoulder", side: "left", cx: 68, cy: 92 },
  { region: "shoulder", side: "right", cx: 132, cy: 92 },
  { region: "hip_flexor", side: "left", cx: 86, cy: 198 },
  { region: "hip_flexor", side: "right", cx: 114, cy: 198 },
  { region: "groin", side: "center", cx: 100, cy: 212 },
  { region: "quad", side: "left", cx: 84, cy: 250 },
  { region: "quad", side: "right", cx: 116, cy: 250 },
  { region: "adductor", side: "left", cx: 92, cy: 240 },
  { region: "adductor", side: "right", cx: 108, cy: 240 },
  { region: "knee_anterior", side: "left", cx: 84, cy: 300 },
  { region: "knee_anterior", side: "right", cx: 116, cy: 300 },
  { region: "shin", side: "left", cx: 84, cy: 340 },
  { region: "shin", side: "right", cx: 116, cy: 340 },
  { region: "ankle", side: "left", cx: 84, cy: 384 },
  { region: "ankle", side: "right", cx: 116, cy: 384 },
  { region: "foot_fore", side: "left", cx: 82, cy: 406 },
  { region: "foot_fore", side: "right", cx: 118, cy: 406 },
];

const BACK_ZONES: BodyZone[] = [
  { region: "upper_back", side: "center", cx: 100, cy: 118 },
  { region: "lower_back", side: "center", cx: 100, cy: 178 },
  { region: "glute", side: "left", cx: 86, cy: 208 },
  { region: "glute", side: "right", cx: 114, cy: 208 },
  { region: "it_band", side: "left", cx: 70, cy: 250 },
  { region: "it_band", side: "right", cx: 130, cy: 250 },
  { region: "hamstring", side: "left", cx: 84, cy: 262 },
  { region: "hamstring", side: "right", cx: 116, cy: 262 },
  { region: "knee_posterior", side: "left", cx: 84, cy: 300 },
  { region: "knee_posterior", side: "right", cx: 116, cy: 300 },
  { region: "calf", side: "left", cx: 84, cy: 344 },
  { region: "calf", side: "right", cx: 116, cy: 344 },
  { region: "achilles", side: "left", cx: 84, cy: 378 },
  { region: "achilles", side: "right", cx: 116, cy: 378 },
  { region: "foot_heel", side: "left", cx: 82, cy: 402 },
  { region: "foot_heel", side: "right", cx: 118, cy: 402 },
];

// Crude humanoid outline shared by both views.
const SILHOUETTE =
  "M100 18 c-12 0 -20 9 -20 22 c0 9 5 16 11 19 l-3 6 " +
  "c-18 4 -28 14 -28 32 l0 46 c0 8 3 14 7 18 l-4 60 " +
  "c-2 14 6 18 6 30 l-2 70 c-1 12 -2 24 -8 36 l-2 22 " +
  "c14 4 22 0 24 -8 l6 -60 l4 -64 l4 64 l6 60 " +
  "c2 8 10 12 24 8 l-2 -22 c-6 -12 -7 -24 -8 -36 l-2 -70 " +
  "c0 -12 8 -16 6 -30 l-4 -60 c4 -4 7 -10 7 -18 l0 -46 " +
  "c0 -18 -10 -28 -28 -32 l-3 -6 c6 -3 11 -10 11 -19 c0 -13 -8 -22 -20 -22 z";

interface BodyMapProps {
  highlighted?: Set<string>; // `${region}:${side}` keys to mark as active niggles
  onSelect: (zone: BodyZone) => void;
}

function zoneKey(region: BodyRegion, side: Side): string {
  return `${region}:${side}`;
}

export function BodyMap({ highlighted, onSelect }: BodyMapProps) {
  const [view, setView] = useState<"front" | "back">("front");
  const zones = view === "front" ? FRONT_ZONES : BACK_ZONES;

  return (
    <div>
      <div className="mb-2 flex justify-center gap-2">
        {(["front", "back"] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={`rounded-full px-4 py-1 text-sm ${
              view === v ? "bg-slate-100 text-slate-900" : "bg-slate-800 text-slate-300"
            }`}
          >
            {v === "front" ? "Face" : "Dos"}
          </button>
        ))}
      </div>

      <svg viewBox="0 0 200 430" className="mx-auto w-56" role="img" aria-label="Carte du corps">
        <path d={SILHOUETTE} fill="#1e293b" stroke="#334155" strokeWidth={1.5} />
        {zones.map((z) => {
          const active = highlighted?.has(zoneKey(z.region, z.side));
          return (
            <circle
              key={zoneKey(z.region, z.side)}
              cx={z.cx}
              cy={z.cy}
              r={9}
              className="cursor-pointer"
              fill={active ? "#dc2626" : "#64748b"}
              fillOpacity={active ? 0.9 : 0.55}
              stroke={active ? "#fecaca" : "#94a3b8"}
              strokeWidth={1}
              onClick={() => onSelect(z)}
            >
              <title>
                {REGION_LABEL[z.region]}
                {z.side !== "center" ? ` (${z.side === "left" ? "gauche" : "droite"})` : ""}
              </title>
            </circle>
          );
        })}
      </svg>
      <p className="mt-1 text-center text-xs text-slate-500">Tape une zone pour signaler une gêne.</p>
    </div>
  );
}
