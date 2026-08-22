"""Security primitives: password hashing and JWT token handling."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def _create_token(subject: str, role: str, expires_minutes: int, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str) -> str:
    """Create a signed JWT access token for the given user id and role."""
    return _create_token(subject, role, settings.JWT_EXPIRATION_MINUTES, "access")


def create_refresh_token(subject: str, role: str) -> str:
    """Create a signed JWT refresh token."""
    return _create_token(
        subject, role, settings.JWT_REFRESH_EXPIRATION_MINUTES, "refresh"
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT. Returns the payload or ``None`` if invalid."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        return None
