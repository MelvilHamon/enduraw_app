"""CLI to fill the database with synthetic athlete cohorts.

Run from the project root so ``app`` is importable::

    python -m scripts.seed --personas 5 --seed 42 --days 180 --reset

``--reset`` drops and recreates every table first. Without it, re-seeding the
same ``(persona, seed)`` is idempotent (the per-athlete rows are rewritten).
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, select

import app.models  # noqa: F401 — register every model on Base.metadata
from app.db import Base, SessionLocal, engine
from app.models.daily_checkin import DailyCheckin
from app.models.daily_metric import DailyMetric
from app.models.illness_flag import IllnessFlag
from app.models.mini_test import MiniTest
from app.models.niggle import Niggle, NiggleReport
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.synth import PRESETS, generate_cohort
from app.synth.seeder import seed_cohort

_COUNTED = (
    ("users", User),
    ("daily_metrics", DailyMetric),
    ("session_feedbacks", SessionFeedback),
    ("daily_checkins", DailyCheckin),
    ("mini_tests", MiniTest),
    ("niggles", Niggle),
    ("niggle_reports", NiggleReport),
    ("illness_flags", IllnessFlag),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic athlete data into the database.")
    parser.add_argument("--personas", type=int, default=5, help="Number of athletes to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Base RNG seed (per-persona offset).")
    parser.add_argument("--days", type=int, default=180, help="History length per athlete.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    preset_names = list(PRESETS)
    specs = [(preset_names[i % len(preset_names)], args.seed + i) for i in range(args.personas)]
    datasets = generate_cohort(specs, days=args.days)

    with SessionLocal() as db:
        users = seed_cohort(db, datasets)
        print(f"Seeded {len(users)} athlete(s) ({args.days} days each):")
        for name, model in _COUNTED:
            total = db.scalar(select(func.count()).select_from(model)) or 0
            print(f"  {name:<18} {total}")


if __name__ == "__main__":
    main()
