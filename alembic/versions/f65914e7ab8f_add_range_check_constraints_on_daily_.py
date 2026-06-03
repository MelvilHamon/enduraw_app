"""add range CHECK constraints on daily_metrics numeric columns

Revision ID: f65914e7ab8f
Revises: d48d92815ec6
Create Date: 2026-06-04 00:40:13.293604

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f65914e7ab8f"
down_revision: str | None = "d48d92815ec6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (constraint name, CHECK condition) — all columns are nullable, so CHECK does
# not fire on NULL (standard SQL behaviour).
_CHECKS: list[tuple[str, str]] = [
    ("ck_daily_metrics_sleep_score", "sleep_score >= 0 AND sleep_score <= 100"),
    ("ck_daily_metrics_stress", "stress >= 0 AND stress <= 100"),
    ("ck_daily_metrics_body_battery", "body_battery >= 0 AND body_battery <= 100"),
    (
        "ck_daily_metrics_training_readiness",
        "training_readiness >= 0 AND training_readiness <= 100",
    ),
    ("ck_daily_metrics_sleep_duration_min", "sleep_duration_min >= 0"),
    ("ck_daily_metrics_rhr", "rhr >= 0"),
    ("ck_daily_metrics_hrv_rmssd", "hrv_rmssd >= 0"),
    ("ck_daily_metrics_resp_rate", "resp_rate >= 0"),
    ("ck_daily_metrics_vo2max", "vo2max >= 0"),
]


def upgrade() -> None:
    with op.batch_alter_table("daily_metrics", schema=None) as batch_op:
        for name, condition in _CHECKS:
            batch_op.create_check_constraint(name, condition)


def downgrade() -> None:
    with op.batch_alter_table("daily_metrics", schema=None) as batch_op:
        for name, _ in reversed(_CHECKS):
            batch_op.drop_constraint(name, type_="check")
