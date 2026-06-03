"""Business logic for mini-tests (stores ``type`` + typed ``payload``)."""

from __future__ import annotations

from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MiniTestType
from app.models.mini_test import MiniTest
from app.schemas.mini_test import MiniTestCreate


def create_mini_test(db: Session, user_id: str, payload: MiniTestCreate) -> MiniTest:
    """Persist a mini-test, peeling ``type`` off the discriminated payload."""

    mini_test = MiniTest(
        user_id=user_id,
        date=payload.date,
        reported_at=payload.reported_at,
        type=MiniTestType(payload.data.type),
        payload=payload.data.model_dump(exclude={"type"}),
    )
    db.add(mini_test)
    db.commit()
    db.refresh(mini_test)
    return mini_test


def list_mini_tests(
    db: Session,
    user_id: str,
    *,
    type_: MiniTestType | None,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[MiniTest]:
    """List the user's mini-tests, newest first, with optional type/date filters."""

    stmt = select(MiniTest).where(MiniTest.user_id == user_id)
    if type_ is not None:
        stmt = stmt.where(MiniTest.type == type_)
    if date_from is not None:
        stmt = stmt.where(MiniTest.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MiniTest.date <= date_to)
    stmt = stmt.order_by(MiniTest.date.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
