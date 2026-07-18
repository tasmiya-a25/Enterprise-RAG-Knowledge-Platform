"""
Core security primitives: password hashing (bcrypt) and JWT
access/refresh token issuance + verification.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from jose import jwt, JWTError

from app.config.settings import get_settings

settings = get_settings()

# NOTE: we use the `bcrypt` library directly rather than passlib's
# CryptContext wrapper. passlib 1.7.4 (the latest release) has a known
# incompatibility with bcrypt>=4.1 that raises a spurious
# "password cannot be longer than 72 bytes" error on every hash/verify
# call, because its internal self-test misreads the newer bcrypt API.
# Calling `bcrypt` directly sidesteps that entirely and is one less
# (largely unmaintained) dependency.
_BCRYPT_MAX_BYTES = 72  # bcrypt's real, hard limit -- we truncate to match


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))


def _create_token(subject: str, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> str:
    """Returns the user_id (sub) encoded in the token, or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError("Could not validate token") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token")

    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError("Token missing subject")
    return sub
