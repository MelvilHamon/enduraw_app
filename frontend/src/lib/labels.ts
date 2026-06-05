import type { BodyRegion, Reco } from "../api/types";

export const RECO_LABEL: Record<Reco, string> = {
  train_as_planned: "Entraîne-toi comme prévu",
  lighten: "Allège ta séance",
  rest: "Repos aujourd'hui",
  consult_physio: "Consulte un physio",
};

// Tailwind background classes per reco (see tailwind.config.js `reco` colors).
export const RECO_BG: Record<Reco, string> = {
  train_as_planned: "bg-reco-good",
  lighten: "bg-reco-lighten",
  rest: "bg-reco-rest",
  consult_physio: "bg-reco-physio",
};

export const REGION_LABEL: Record<BodyRegion, string> = {
  foot_fore: "Avant-pied",
  foot_mid: "Médio-pied",
  foot_heel: "Talon",
  ankle: "Cheville",
  achilles: "Achille",
  calf: "Mollet",
  shin: "Tibia",
  knee_anterior: "Genou (avant)",
  knee_medial: "Genou (interne)",
  knee_lateral: "Genou (externe)",
  knee_posterior: "Genou (arrière)",
  quad: "Quadriceps",
  hamstring: "Ischio",
  adductor: "Adducteur",
  it_band: "Bandelette IT",
  hip_flexor: "Fléchisseur hanche",
  glute: "Fessier",
  groin: "Aine",
  lower_back: "Bas du dos",
  upper_back: "Haut du dos",
  neck: "Nuque",
  shoulder: "Épaule",
  other: "Autre",
};
