"""Security primitives: password hashing (bcrypt) and JWT encode/decode.

Kept free of any database dependency so it can be unit-tested in isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

# bcrypt only considers the first 72 bytes of the password.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""

    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""

    try:
        return bcrypt.checkpw(_truncate(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> tuple[str, int]:
    """Create a signed JWT for ``subject``; return (token, expires_in_seconds)."""

    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, minutes * 60


def decode_token(token: str) -> str | None:
    """Return the ``sub`` claim of a valid token, or ``None`` if invalid/expired."""

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
