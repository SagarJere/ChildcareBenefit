"""JWT access token creation and verification.

Version 1 authentication (Employee ID only) issues a short-lived signed
token on login. Every protected endpoint verifies this token and re-reads
the employee's current status from the database rather than trusting the
token's claims for anything beyond identity — see
`app/dependencies/auth.py`. This keeps the trust boundary narrow so an
approved SSO/Entra ID token can replace this issuance mechanism later
without changing how the rest of the backend consumes identity.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings


class TokenError(Exception):
    """Raised when a bearer token is missing, malformed, expired, or
    fails signature verification."""


def create_access_token(*, employee_id: str, memp_id: int) -> str:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set it in the backend "
            "environment before Employee Login can issue tokens."
        )

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": employee_id,
        "memp_id": memp_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set it in the backend "
            "environment before protected endpoints can validate tokens."
        )

    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token.") from exc
