"""Sanity tests for the metric-domain ORM models.

These are deliberately lightweight — they check that the schema enforces what it
should (CHECK / UNIQUE constraints), that the Niggle <-> NiggleReport relationship
and cascade work, and that JSON / enum columns round-trip. Exhaustive behaviour
tests arrive with the CRUD routes in step 3.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    DailyCheckin,
    IllnessFlag,
    MiniTest,
    Niggle,
    NiggleReport,
    SessionFeedback,
    User,
)
from app.models.enums import (
    Affect,
    BodyRegion,
    FeedbackSource,
    MiniTestType,
    PainType,
    Side,
)

_NOW = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
_DAY = date(2026, 6, 1)


def _make_user(db: Session, email: str = "athlete@example.com") -> User:
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    return user


def test_create_daily_checkin_ok(db_session: Session) -> None:
    user = _make_user(db_session)
    checkin = DailyCheckin(
        user_id=user.id,
        date=_DAY,
        form_vs_normal=1,
        motivation=1,
        fatigue=2,
        stress=-1,
        reported_at=_NOW,
    )
    db_session.add(checkin)
    db_session.commit()

    assert checkin.id is not None
    assert checkin.stress == -1
    assert checkin.synced_to_coachagent is False
    assert checkin.created_at is not None and checkin.updated_at is not None


def test_daily_checkin_form_vs_normal_check(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add(
        DailyCheckin(
            user_id=user.id,
            date=_DAY,
            form_vs_normal=5,  # out of [-2, 2]
            motivation=1,
            fatigue=3,
            reported_at=_NOW,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_daily_checkin_motivation_check(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add(
        DailyCheckin(
            user_id=user.id,
            date=_DAY,
            form_vs_normal=0,
            motivation=3,  # out of [-2, 2]
            fatigue=3,
            reported_at=_NOW,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_daily_checkin_unique_user_date(db_session: Session) -> None:
    user = _make_user(db_session)
    for _ in range(2):
        db_session.add(
            DailyCheckin(
                user_id=user.id,
                date=_DAY,
                form_vs_normal=0,
                motivation=1,
                fatigue=3,
                reported_at=_NOW,
            )
        )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_niggle_with_reports_relationship(db_session: Session) -> None:
    user = _make_user(db_session)
    niggle = Niggle(
        user_id=user.id,
        opened_at=_DAY,
        region=BodyRegion.KNEE_ANTERIOR,
        side=Side.LEFT,
        structure="tendon rotulien",
    )
    for i in range(3):
        niggle.reports.append(
            NiggleReport(
                date=date(2026, 6, 1 + i),
                intensity=4 + i,
                pain_type=PainType.DULL,
                is_new_or_recurrent="new",
            )
        )
    db_session.add(niggle)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Niggle, niggle.id)
    assert reloaded is not None
    assert len(reloaded.reports) == 3
    assert {r.intensity for r in reloaded.reports} == {4, 5, 6}


def test_niggle_cascade_delete(db_session: Session) -> None:
    user = _make_user(db_session)
    niggle = Niggle(user_id=user.id, opened_at=_DAY, region=BodyRegion.CALF, side=Side.RIGHT)
    niggle.reports.append(NiggleReport(date=_DAY, intensity=5, is_new_or_recurrent="new"))
    db_session.add(niggle)
    db_session.commit()
    assert db_session.query(NiggleReport).count() == 1

    db_session.delete(niggle)
    db_session.commit()
    assert db_session.query(NiggleReport).count() == 0


def test_mini_test_jump_payload_roundtrip(db_session: Session) -> None:
    user = _make_user(db_session)
    payload = {"flight_time_ms": 480, "height_cm": 28.3}
    mt = MiniTest(
        user_id=user.id,
        date=_DAY,
        reported_at=_NOW,
        type=MiniTestType.JUMP,
        payload=payload,
    )
    db_session.add(mt)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(MiniTest, mt.id)
    assert reloaded is not None
    assert reloaded.type == MiniTestType.JUMP
    assert reloaded.payload == payload


def test_mini_test_reaction_payload_roundtrip(db_session: Session) -> None:
    user = _make_user(db_session)
    payload = {"mean_rt_ms": 312.5, "sd_rt_ms": 41.2, "n_taps": 20}
    mt = MiniTest(
        user_id=user.id,
        date=_DAY,
        reported_at=_NOW,
        type=MiniTestType.REACTION,
        payload=payload,
    )
    db_session.add(mt)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(MiniTest, mt.id)
    assert reloaded is not None
    assert reloaded.payload["n_taps"] == 20


def test_session_feedback_unique_user_activity(db_session: Session) -> None:
    user = _make_user(db_session)
    for _ in range(2):
        db_session.add(
            SessionFeedback(
                user_id=user.id,
                activity_id="act-123",
                rpe=6,
                affect=Affect.NEUTRAL,
                source=FeedbackSource.GARMIN_WATCH,
                reported_at=_NOW,
            )
        )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_session_feedback_rpe_check(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add(
        SessionFeedback(
            user_id=user.id,
            activity_id="act-1",
            rpe=11,  # out of [1, 10]
            affect=Affect.STRONG,
            source=FeedbackSource.APP_MANUAL,
            reported_at=_NOW,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_illness_flag_symptoms_roundtrip(db_session: Session) -> None:
    user = _make_user(db_session)
    flag = IllnessFlag(user_id=user.id, date=_DAY, symptoms=["sore_throat", "fever"])
    db_session.add(flag)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(IllnessFlag, flag.id)
    assert reloaded is not None
    assert reloaded.symptoms == ["sore_throat", "fever"]
    assert reloaded.watch_hint_triggered is False


def test_enum_stored_as_string_value(db_session: Session) -> None:
    user = _make_user(db_session)
    niggle = Niggle(
        user_id=user.id,
        opened_at=_DAY,
        region=BodyRegion.KNEE_ANTERIOR,
        side=Side.BILATERAL,
    )
    db_session.add(niggle)
    db_session.commit()

    # Reloaded as the enum member...
    db_session.expire_all()
    reloaded = db_session.get(Niggle, niggle.id)
    assert reloaded is not None
    assert reloaded.region is BodyRegion.KNEE_ANTERIOR
    # ...but persisted as the raw string value in a VARCHAR column.
    raw = db_session.execute(
        text("SELECT region FROM niggles WHERE id = :id"), {"id": niggle.id}
    ).scalar_one()
    assert raw == "knee_anterior"
