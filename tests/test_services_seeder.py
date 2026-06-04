"""Unit tests for the synthetic dataset seeder (no HTTP, direct DB)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.daily_checkin import DailyCheckin
from app.models.daily_metric import DailyMetric
from app.models.illness_flag import IllnessFlag
from app.models.mini_test import MiniTest
from app.models.niggle import Niggle, NiggleReport
from app.models.session_feedback import SessionFeedback
from app.synth import generate
from app.synth.seeder import email_for, seed_user


def _count(db: Session, model: type, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0


def test_seed_user_counts_match_dataset(db_session: Session) -> None:
    dataset = generate("InjuryProne", seed=7, days=180)
    user = seed_user(db_session, dataset)

    expected_feedbacks = sum(
        1 for s in dataset.sessions if s.rpe is not None and s.affect is not None
    )
    expected_reports = sum(len(n.reports) for n in dataset.niggles)
    confirmed_days = {
        ep.start + timedelta(days=i)
        for ep in dataset.illness_episodes
        for i in range((ep.end - ep.start).days + 1)
    }

    assert _count(db_session, DailyMetric, user.id) == len(dataset.daily_metrics)
    assert _count(db_session, SessionFeedback, user.id) == expected_feedbacks
    assert _count(db_session, DailyCheckin, user.id) == len(dataset.checkins)
    assert _count(db_session, MiniTest, user.id) == len(dataset.mini_tests)
    assert _count(db_session, Niggle, user.id) == len(dataset.niggles)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NiggleReport)
            .join(Niggle, NiggleReport.niggle_id == Niggle.id)
            .where(Niggle.user_id == user.id)
        )
        == expected_reports
    )
    # Every confirmed episode day has a flag (hint-only days may add more).
    assert _count(db_session, IllnessFlag, user.id) >= len(confirmed_days)


def test_seed_user_idempotent(db_session: Session) -> None:
    dataset = generate("PoorSleeper", seed=3, days=150)
    user = seed_user(db_session, dataset)
    counts_first = {
        model.__name__: _count(db_session, model, user.id)
        for model in (DailyMetric, SessionFeedback, DailyCheckin, MiniTest, Niggle, IllnessFlag)
    }

    # Re-seed the same (persona, seed): same user, no duplicated rows.
    user_again = seed_user(db_session, dataset)
    assert user_again.id == user.id
    assert db_session.scalar(select(func.count()).select_from(Niggle.__table__)) == _count(
        db_session, Niggle, user.id
    )
    counts_second = {
        model.__name__: _count(db_session, model, user.id)
        for model in (DailyMetric, SessionFeedback, DailyCheckin, MiniTest, Niggle, IllnessFlag)
    }
    assert counts_first == counts_second


def test_seed_user_email_is_persona_seed_keyed(db_session: Session) -> None:
    dataset = generate("Regular", seed=11, days=90)
    user = seed_user(db_session, dataset)
    assert user.email == email_for(dataset) == "regular-11@synth.enduraw"
    assert user.persona_id == "Regular"


def test_episode_days_carry_confirmed_symptoms(db_session: Session) -> None:
    dataset = generate("InjuryProne", seed=7, days=180)
    user = seed_user(db_session, dataset)

    episode = dataset.illness_episodes[0]
    flag = db_session.scalar(
        select(IllnessFlag).where(IllnessFlag.user_id == user.id, IllnessFlag.date == episode.start)
    )
    assert flag is not None
    assert flag.confirmed_by_user is True
    assert set(flag.symptoms) == {s.value for s in episode.symptoms}


def test_seed_sets_watch_hint_on_some_episode_day(db_session: Session) -> None:
    dataset = generate("InjuryProne", seed=7, days=180)
    user = seed_user(db_session, dataset)

    episode_days = {
        ep.start + timedelta(days=i)
        for ep in dataset.illness_episodes
        for i in range((ep.end - ep.start).days + 1)
    }
    triggered_days = set(
        db_session.scalars(
            select(IllnessFlag.date).where(
                IllnessFlag.user_id == user.id,
                IllnessFlag.watch_hint_triggered.is_(True),
            )
        ).all()
    )
    assert triggered_days & episode_days


def test_seed_is_deterministic_across_sessions(db_session: Session) -> None:
    """Same (persona, seed) ⇒ identical persisted counts."""

    user_a = seed_user(db_session, generate("OverTrainer", seed=5, days=120))
    counts_a = {
        m.__name__: _count(db_session, m, user_a.id)
        for m in (DailyMetric, SessionFeedback, DailyCheckin, MiniTest, Niggle)
    }
    # A second, structurally identical dataset under a different seed/persona is
    # a separate athlete; regenerating the *same* spec must reproduce counts.
    user_b = seed_user(db_session, generate("OverTrainer", seed=5, days=120))
    assert user_b.id == user_a.id  # same email key ⇒ re-seeded in place
    counts_b = {
        m.__name__: _count(db_session, m, user_b.id)
        for m in (DailyMetric, SessionFeedback, DailyCheckin, MiniTest, Niggle)
    }
    assert counts_a == counts_b
