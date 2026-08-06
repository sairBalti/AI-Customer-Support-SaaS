"""JWT create/verify helpers for access tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.core.config import get_settings
from app.domain.exceptions.auth import TokenExpiredError, TokenInvalidError

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"


def create_access_token(
    *,
    user_id: int,
    company_id: int,
    role_name: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "company_id": company_id,
        "role": role_name,
        "type": TOKEN_TYPE_ACCESS,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token. Raises domain auth errors."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except JWTError as exc:
        raise TokenInvalidError() from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise TokenInvalidError("Token type is not an access token.")
    if "sub" not in payload or "company_id" not in payload:
        raise TokenInvalidError("Token claims are incomplete.")
    return payload
