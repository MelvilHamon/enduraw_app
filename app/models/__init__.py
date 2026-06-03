"""ORM models package.

Importing every model here ensures they are registered on ``Base.metadata``
so Alembic autogenerate sees all tables.
"""

from app.models.user import User

__all__ = ["User"]
