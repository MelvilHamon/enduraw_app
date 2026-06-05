import type { Reco } from "../api/types";
import { RECO_BG, RECO_LABEL } from "../lib/labels";

export function RecoBadge({ reco }: { reco: Reco }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold text-white ${RECO_BG[reco]}`}
    >
      {RECO_LABEL[reco]}
    </span>
  );
}
