"""Persist a :class:`~app.synth.dataset.SyntheticDataset` into the database.

The seeder reuses the step-3 services and the step-5 Garmin ingestion so the
written data is identical to what the live endpoints would produce — including
the illness watch-hint, which is computed by ingesting the daily metrics. It is
idempotent: re-seeding the same ``(persona, seed)`` wipes that athlete's rows
and rewrites them, so counts stay stable and no duplicates accumulate.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from datetime import date as date_
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.engines.snapshot import write_snapshot
from app.models.daily_checkin import DailyCheckin
from app.models.daily_metric import DailyMetric
from app.models.illness_flag import IllnessFlag
from app.models.mini_test import MiniTest
from app.models.niggle import Niggle, NiggleReport
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.schemas.checkin import CheckinCreate
from app.schemas.feedback import SessionFeedbackCreate
from app.schemas.garmin import GarminDaily, GarminSessionFeedback
from app.schemas.illness import IllnessCreate
from app.security import hash_password
from app.services import checkin_service, feedback_service, garmin_service, illness_service
from app.synth.dataset import SyntheticDailyMetric, SyntheticDataset

# Hashed once at import — synthetic users never log in, this is a placeholder.
_PLACEHOLDER_PASSWORD_HASH = hash_password("synthetic-seed-user")

# Deterministic clock-time stamped on date-only synthetic events.
_DEFAULT_REPORT_TIME = time(18, 0)


def email_for(dataset: SyntheticDataset) -> str:
    """Stable e-mail that keys a synthetic athlete by ``(persona, seed)``."""

    return f"{dataset.persona_name.lower()}-{dataset.seed}@synth.enduraw"


def _reported_at(day: date_) -> datetime:
    """Combine a synthetic ``date`` with the default reporting time (UTC)."""

    return datetime.combine(day, _DEFAULT_REPORT_TIME, tzinfo=UTC)


def _to_garmin_daily(metric: SyntheticDailyMetric) -> GarminDaily:
    return GarminDaily(
        date=metric.date,
        sleep_score=metric.sleep_score,
        sleep_duration_min=metric.sleep_duration_min,
        sleep_onset=metric.sleep_onset,
        sleep_wake=metric.sleep_wake,
        hrv_rmssd=metric.hrv_rmssd,
        hrv_status=metric.hrv_status,
        rhr=metric.rhr,
        stress=metric.stress,
        body_battery=metric.body_battery,
        resp_rate=metric.resp_rate,
        training_readiness=metric.training_readiness,
        vo2max=metric.vo2max,
        source=metric.source,
    )


def _upsert_user(db: Session, dataset: SyntheticDataset) -> User:
    email = email_for(dataset)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            hashed_password=_PLACEHOLDER_PASSWORD_HASH,
            persona_id=dataset.persona_name,
        )
        db.add(user)
    else:
        user.persona_id = dataset.persona_name
    db.commit()
    db.refresh(user)
    return user


def _wipe_user_data(db: Session, user_id: str) -> None:
    """Remove every data row owned by ``user_id`` (reports first, then niggles)."""

    niggle_ids = list(db.scalars(select(Niggle.id).where(Niggle.user_id == user_id)).all())
    if niggle_ids:
        db.execute(delete(NiggleReport).where(NiggleReport.niggle_id.in_(niggle_ids)))
    for model in (Niggle, MiniTest, DailyMetric, SessionFeedback, DailyCheckin, IllnessFlag):
        db.execute(delete(model).where(model.user_id == user_id))
    db.commit()


def _seed_garmin(db: Session, user: User, dataset: SyntheticDataset) -> None:
    """Daily metrics (+ watch hints) and on-watch session RPE via ingestion."""

    garmin_service.ingest_daily(db, user.id, [_to_garmin_daily(m) for m in dataset.daily_metrics])

    watch_rows: list[GarminSessionFeedback] = []
    for session in dataset.sessions:
        if session.rpe is None or session.affect is None:
            continue
        reported_at = _reported_at(session.date)
        if session.rpe_filled_on_watch:
            watch_rows.append(
                GarminSessionFeedback(
                    activity_id=session.activity_id,
                    rpe=session.rpe,
                    affect=session.affect,
                    reported_at=reported_at,
                )
            )
        else:
            feedback_service.upsert_feedback(
                db,
                user.id,
                SessionFeedbackCreate(
                    activity_id=session.activity_id,
                    rpe=session.rpe,
                    affect=session.affect,
                    reported_at=reported_at,
                ),
            )
    garmin_service.ingest_session_feedback(db, user.id, watch_rows)


def _seed_checkins(db: Session, user: User, dataset: SyntheticDataset) -> None:
    for checkin in dataset.checkins:
        checkin_service.upsert_checkin(
            db,
            user.id,
            CheckinCreate(
                date=checkin.date,
                form_vs_normal=checkin.form_vs_normal,
                motivation=checkin.motivation,
                fatigue=checkin.fatigue,
            ),
        )


def _seed_mini_tests(db: Session, user: User, dataset: SyntheticDataset) -> None:
    for mini_test in dataset.mini_tests:
        db.add(
            MiniTest(
                user_id=user.id,
                date=mini_test.date,
                reported_at=mini_test.reported_at,
                type=mini_test.type,
                payload=mini_test.payload,
            )
        )
    db.commit()


def _seed_niggles(db: Session, user: User, dataset: SyntheticDataset) -> None:
    for niggle in dataset.niggles:
        row = Niggle(
            user_id=user.id,
            opened_at=niggle.opened_at,
            closed_at=niggle.closed_at,
            region=niggle.region,
            side=niggle.side,
            structure=niggle.structure,
        )
        db.add(row)
        db.flush()  # assign row.id before attaching reports
        for report in niggle.reports:
            db.add(
                NiggleReport(
                    niggle_id=row.id,
                    date=report.date,
                    intensity=report.intensity,
                    pain_type=report.pain_type,
                    mechanical_pattern=report.mechanical_pattern,
                    timing=report.timing,
                    is_new_or_recurrent=report.is_new_or_recurrent,
                    linked_activity_id=report.linked_activity_id,
                    notes=report.notes,
                )
            )
    db.commit()


def _seed_illness(db: Session, user: User, dataset: SyntheticDataset) -> None:
    """Confirm each illness-episode day, preserving any hint set during ingestion."""

    for episode in dataset.illness_episodes:
        day = episode.start
        while day <= episode.end:
            illness_service.upsert_illness(
                db,
                user.id,
                IllnessCreate(date=day, symptoms=list(episode.symptoms), notes=None),
            )
            day += timedelta(days=1)


def seed_user(
    db: Session, dataset: SyntheticDataset, *, engine_dir: str | Path | None = None
) -> User:
    """Idempotently persist one synthetic athlete and all their data.

    When ``engine_dir`` is given, also dump the generator's latent truth (and the
    session log) to ``{engine_dir}/{user_id}.json`` so the standalone
    :class:`~app.engines.mock.MockEngine` can serve this athlete.
    """

    user = _upsert_user(db, dataset)
    _wipe_user_data(db, user.id)
    _seed_garmin(db, user, dataset)
    _seed_checkins(db, user, dataset)
    _seed_mini_tests(db, user, dataset)
    _seed_niggles(db, user, dataset)
    _seed_illness(db, user, dataset)
    if engine_dir is not None:
        write_snapshot(engine_dir, user.id, latent=dataset.latent, sessions=dataset.sessions)
    return user


def seed_cohort(
    db: Session, datasets: list[SyntheticDataset], *, engine_dir: str | Path | None = None
) -> list[User]:
    """Seed a whole cohort, returning the created/updated users."""

    return [seed_user(db, dataset, engine_dir=engine_dir) for dataset in datasets]
