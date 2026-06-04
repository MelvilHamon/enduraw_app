"""Business logic for illness flags (upsert by ``(user_id, date)``)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_metric import DailyMetric
from app.models.illness_flag import IllnessFlag
from app.schemas.illness import IllnessCreate

# Rolling, strictly-causal baseline used by the watch-hint heuristic.
WATCH_HINT_WINDOW_DAYS = 14
WATCH_HINT_MIN_OBS = 7


def upsert_illness(db: Session, user_id: str, payload: IllnessCreate) -> tuple[IllnessFlag, bool]:
    """Create or update the illness flag for ``(user_id, date)``.

    The athlete is posting it, so ``confirmed_by_user`` is always ``True`` and
    ``watch_hint_triggered`` stays ``False`` (set by ingestion in a later step).
    Returns ``(flag, created)``.
    """

    day = payload.date or datetime.now(UTC).date()
    symptoms = [symptom.value for symptom in payload.symptoms]
    existing = db.scalar(
        select(IllnessFlag).where(
            IllnessFlag.user_id == user_id,
            IllnessFlag.date == day,
        )
    )
    if existing is not None:
        existing.symptoms = symptoms
        existing.notes = payload.notes
        existing.confirmed_by_user = True
        db.commit()
        db.refresh(existing)
        return existing, False

    flag = IllnessFlag(
        user_id=user_id,
        date=day,
        symptoms=symptoms,
        notes=payload.notes,
        confirmed_by_user=True,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag, True


def list_illness(
    db: Session,
    user_id: str,
    *,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[IllnessFlag]:
    """List the user's illness flags, newest first, within an optional date window."""

    stmt = select(IllnessFlag).where(IllnessFlag.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(IllnessFlag.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(IllnessFlag.date <= date_to)
    stmt = stmt.order_by(IllnessFlag.date.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@dataclass(frozen=True)
class WatchHint:
    """The watch-hint computation for one day vs the athlete's rolling baseline."""

    triggered: bool
    hrv_delta: float | None
    rhr_delta: float | None
    resp_delta: float | None
    baseline_window_days: int


def _mean_std(values: list[float]) -> tuple[float, float] | None:
    """Return ``(mean, population_std)`` when there are enough observations."""

    if len(values) < WATCH_HINT_MIN_OBS:
        return None
    return statistics.fmean(values), statistics.pstdev(values)


def compute_hint(
    db: Session,
    user_id: str,
    day: date_,
    *,
    window_days: int = WATCH_HINT_WINDOW_DAYS,
) -> WatchHint:
    """Compute the illness watch-hint for ``day`` against a causal baseline.

    The baseline is the trailing ``window_days`` of ``daily_metrics`` strictly
    *before* ``day`` (the current day is excluded — no future leakage). Each of
    HRV, RHR and respiration needs at least ``WATCH_HINT_MIN_OBS`` non-null
    observations; otherwise the hint cannot fire. It triggers when the day looks
    sick on all three axes at once::

        hrv_rmssd < μ_hrv − σ_hrv  AND  rhr > μ_rhr + σ_rhr  AND  resp > μ_resp + σ_resp
    """

    current = db.scalar(
        select(DailyMetric).where(DailyMetric.user_id == user_id, DailyMetric.date == day)
    )
    window = list(
        db.scalars(
            select(DailyMetric).where(
                DailyMetric.user_id == user_id,
                DailyMetric.date >= day - timedelta(days=window_days),
                DailyMetric.date < day,
            )
        ).all()
    )

    hrv = _mean_std([m.hrv_rmssd for m in window if m.hrv_rmssd is not None])
    rhr = _mean_std([float(m.rhr) for m in window if m.rhr is not None])
    resp = _mean_std([m.resp_rate for m in window if m.resp_rate is not None])

    cur_hrv = current.hrv_rmssd if current is not None else None
    cur_rhr = float(current.rhr) if current is not None and current.rhr is not None else None
    cur_resp = current.resp_rate if current is not None else None

    hrv_delta = cur_hrv - hrv[0] if hrv is not None and cur_hrv is not None else None
    rhr_delta = cur_rhr - rhr[0] if rhr is not None and cur_rhr is not None else None
    resp_delta = cur_resp - resp[0] if resp is not None and cur_resp is not None else None

    triggered = (
        hrv is not None
        and rhr is not None
        and resp is not None
        and cur_hrv is not None
        and cur_rhr is not None
        and cur_resp is not None
        and cur_hrv < hrv[0] - hrv[1]
        and cur_rhr > rhr[0] + rhr[1]
        and cur_resp > resp[0] + resp[1]
    )

    return WatchHint(
        triggered=triggered,
        hrv_delta=hrv_delta,
        rhr_delta=rhr_delta,
        resp_delta=resp_delta,
        baseline_window_days=len(window),
    )


def set_watch_hint(db: Session, user_id: str, day: date_, triggered: bool) -> bool:
    """Reflect the freshly computed watch-hint onto the ``(user_id, day)`` flag.

    Only ``watch_hint_triggered`` is touched — ``confirmed_by_user``,
    ``symptoms`` and ``notes`` (the athlete's own input) are never altered. An
    empty flag is created only when the hint fires and none exists yet; a
    non-triggering day with no flag is a no-op. Returns the resulting
    ``watch_hint_triggered`` value.
    """

    existing = db.scalar(
        select(IllnessFlag).where(IllnessFlag.user_id == user_id, IllnessFlag.date == day)
    )
    if existing is not None:
        existing.watch_hint_triggered = triggered
        db.commit()
        return triggered

    if not triggered:
        return False

    flag = IllnessFlag(
        user_id=user_id,
        date=day,
        symptoms=[],
        watch_hint_triggered=True,
        confirmed_by_user=False,
    )
    db.add(flag)
    db.commit()
    return True
