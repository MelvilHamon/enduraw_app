"""ORM models package.

Importing every model here ensures they are registered on ``Base.metadata``
so Alembic autogenerate sees all tables.
"""

from app.models.daily_checkin import DailyCheckin
from app.models.daily_metric import DailyMetric
from app.models.illness_flag import IllnessFlag
from app.models.mini_test import MiniTest
from app.models.niggle import Niggle, NiggleReport
from app.models.session_feedback import SessionFeedback
from app.models.user import User

__all__ = [
    "User",
    "DailyCheckin",
    "Niggle",
    "NiggleReport",
    "MiniTest",
    "DailyMetric",
    "SessionFeedback",
    "IllnessFlag",
]
