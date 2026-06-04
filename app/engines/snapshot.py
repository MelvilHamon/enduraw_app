"""On-disk format for the standalone engine's per-user data.

There is no ``activities`` / ``engine_state`` table — CoachAgent owns that data.
For standalone runs the step-5 seeder dumps the generator's latent truth
(fitness / fatigue / form / acwr / daily_load) and the session log to one JSON
file per user under ``MOCK_ENGINE_DIR``; :class:`~app.engines.mock.MockEngine`
reads it back. This module is the single source of truth for that format and is
deliberately free of any ``app.synth`` import at runtime (the writer passes the
synth objects in), so the engine layer stays independent of the generator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date as date_
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.engines.errors import EngineNotFound

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a runtime synth import
    from collections.abc import Sequence

    from app.synth.dataset import LatentState, SyntheticSession

_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EngineSnapshot:
    """One athlete's latent engine truth, parsed from disk.

    The five series are parallel arrays aligned on ``dates`` (one entry per
    calendar day). ``activities`` are kept as raw dicts and validated into
    :class:`~app.engines.schemas.EngineActivity` by the caller.
    """

    dates: list[date_]
    daily_load: list[float]
    fitness: list[float]
    fatigue: list[float]
    form: list[float]
    acwr: list[float | None]
    activities: list[dict[str, Any]]


def _path(base_dir: str | Path, user_id: str) -> Path:
    return Path(base_dir) / f"{user_id}.json"


def write_snapshot(
    base_dir: str | Path,
    user_id: str,
    *,
    latent: LatentState,
    sessions: Sequence[SyntheticSession],
) -> Path:
    """Serialise ``latent`` + ``sessions`` for ``user_id`` and return the file path."""

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "user_id": user_id,
        "dates": [d.isoformat() for d in latent.dates],
        "daily_load": list(latent.daily_load),
        "fitness": list(latent.fitness),
        "fatigue": list(latent.fatigue),
        "form": list(latent.form),
        "acwr": list(latent.acwr),
        "activities": [
            {
                "id": s.activity_id,
                "date": s.date.isoformat(),
                "type": s.session_type,
                "duration_s": s.duration_s,
                "distance_m": s.distance_m,
                "trimp": s.trimp,
                "hr_tss": s.hr_tss,
                "elevation_gain_m": s.elevation_gain_m,
            }
            for s in sessions
        ],
    }

    path = _path(base_dir, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def load_snapshot(base_dir: str | Path, user_id: str) -> EngineSnapshot:
    """Read the snapshot for ``user_id`` (raises ``EngineNotFound`` if missing)."""

    path = _path(base_dir, user_id)
    if not path.is_file():
        raise EngineNotFound(f"No engine snapshot for user {user_id!r} under {base_dir}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return EngineSnapshot(
        dates=[date_.fromisoformat(d) for d in raw["dates"]],
        daily_load=list(raw["daily_load"]),
        fitness=list(raw["fitness"]),
        fatigue=list(raw["fatigue"]),
        form=list(raw["form"]),
        acwr=list(raw["acwr"]),
        activities=list(raw["activities"]),
    )
