"""Per-persona integration: seed synth athletes and read them end-to-end.

Closes the step4→7 loop — the generator's latent truth (engine snapshot) plus the
ingested app/Garmin data flow all the way through the fusion service. Assertions
scan the full history (a characteristic signal must surface *somewhere*) rather
than pinning a single day, so they stay robust to generator tuning.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.engines.mock import MockEngine
from app.fusion import service as fusion_service
from app.fusion.readiness import DailyRead, Reco
from app.fusion.signals import SignalKey
from app.synth import generate
from app.synth.seeder import seed_user

_END = date(2026, 6, 4)
_DAYS = 180
_SCAN = 145  # days back from _END with enough history to reason over

_ALL_KEYS: set[SignalKey] = {
    "divergence_subj_obj",
    "illness_hint",
    "niggle_escalation",
    "niggle_load_correlation",
    "wellness_divergence",
    "mini_test_trend",
}


def _seed(db: Session, tmp_path: Path, persona: str, seed: int) -> tuple[object, MockEngine]:
    dataset = generate(persona, seed=seed, days=_DAYS, end_date=_END)
    user = seed_user(db, dataset, engine_dir=tmp_path)
    return user, MockEngine(user.id, str(tmp_path))


async def _scan(
    db: Session, user: object, engine: MockEngine
) -> tuple[Counter[Reco], Counter[SignalKey], list[DailyRead]]:
    recos: Counter[Reco] = Counter()
    fired: Counter[SignalKey] = Counter()
    reads: list[DailyRead] = []
    for i in range(_SCAN):
        read = await fusion_service.compute_daily_read(db, user, _END - timedelta(days=i), engine)  # type: ignore[arg-type]
        recos[read.readiness.reco] += 1
        for s in read.signals:
            if s.triggered:
                fired[s.key] += 1
        reads.append(read)
    return recos, fired, reads


async def test_overtrainer_diverges_and_backs_off(db_session: Session, tmp_path: Path) -> None:
    user, engine = _seed(db_session, tmp_path, "OverTrainer", 7)
    recos, fired, reads = await _scan(db_session, user, engine)
    assert fired["divergence_subj_obj"] > 0  # the anchor gap surfaces
    assert recos[Reco.LIGHTEN] + recos[Reco.REST] > 0
    assert all(r.engine_state is not None for r in reads)  # snapshot covers the scan


async def test_injuryprone_escalates_to_consult_physio(db_session: Session, tmp_path: Path) -> None:
    user, engine = _seed(db_session, tmp_path, "InjuryProne", 7)
    recos, fired, _ = await _scan(db_session, user, engine)
    assert fired["niggle_escalation"] > 0
    assert recos[Reco.CONSULT_PHYSIO] > 0


async def test_poorsleeper_flags_wellness(db_session: Session, tmp_path: Path) -> None:
    user, engine = _seed(db_session, tmp_path, "PoorSleeper", 3)
    _, fired, _ = await _scan(db_session, user, engine)
    assert fired["wellness_divergence"] > 0


async def test_regular_mostly_trains_as_planned(db_session: Session, tmp_path: Path) -> None:
    user, engine = _seed(db_session, tmp_path, "Regular", 11)
    recos, _, _ = await _scan(db_session, user, engine)
    assert recos[Reco.CONSULT_PHYSIO] == 0
    assert max(recos, key=lambda r: recos[r]) == Reco.TRAIN_AS_PLANNED


async def test_daily_read_shape_invariants(db_session: Session, tmp_path: Path) -> None:
    user, engine = _seed(db_session, tmp_path, "Regular", 11)
    read = await fusion_service.compute_daily_read(db_session, user, _END, engine)  # type: ignore[arg-type]
    assert 0.0 <= read.composite_score <= 1.0
    assert {s.key for s in read.signals} == _ALL_KEYS
    assert len(read.readiness.top_2) <= 2
