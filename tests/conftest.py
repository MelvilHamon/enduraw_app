"""Shared test fixtures: in-memory DB and a TestClient with overridden get_db."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models.user import User
from app.security import create_access_token, hash_password


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection: object, _: object) -> None:
    # SQLite ignores ON DELETE CASCADE unless foreign key enforcement is on.
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Hash the test password exactly once for the whole suite: bcrypt is by far the
# slowest thing the integration tests would otherwise do (once per request).
_TEST_PASSWORD_HASH = hash_password("supersecret123")


def make_auth_headers(db: Session, email: str) -> dict[str, str]:
    """Insert a user directly and mint a Bearer header for it.

    The full register/login HTTP flow is covered by ``test_auth.py``; resource
    tests only need an authenticated identity, so we skip the bcrypt round-trip.
    """

    user = User(email=email, hashed_password=_TEST_PASSWORD_HASH)
    db.add(user)
    db.commit()
    token, _ = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    """Bearer header for the primary test athlete."""

    return make_auth_headers(db_session, "athlete@example.com")


@pytest.fixture
def other_auth_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    """Bearer header for a second, distinct athlete (for isolation tests)."""

    return make_auth_headers(db_session, "intruder@example.com")
