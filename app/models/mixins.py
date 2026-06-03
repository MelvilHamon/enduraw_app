"""Reusable declarative mixins and column helpers shared by ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

_E = TypeVar("_E", bound=Enum)


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


def str_enum(enum_cls: type[_E]) -> sa.Enum:
    """Return a ``VARCHAR``-backed enum column type for ``enum_cls``.

    ``native_enum=False`` stores the member *value* (e.g. ``"foot_fore"``) in a
    plain ``VARCHAR`` and emits a ``CHECK col IN (...)`` constraint listing the
    allowed values — no native SQL ``ENUM`` type, so SQLite and PostgreSQL match.
    """

    return sa.Enum(
        enum_cls,
        native_enum=False,
        length=max(len(member.value) for member in enum_cls),
        values_callable=lambda enum: [member.value for member in enum],
        validate_strings=True,
    )


class TimestampMixin:
    """Adds automatic ``created_at`` / ``updated_at`` columns to a model.

    Defaults are applied Python-side (consistent with the ``User`` model from
    step 1); ``updated_at`` is refreshed on every ``UPDATE`` via ``onupdate``.
    """

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
