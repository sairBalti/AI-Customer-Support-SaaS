"""User validation helpers (users.md password & field rules)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.domain.exceptions.user import UserValidationError

_PASSWORD_SPECIAL = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,100}$")

SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "email",
        "first_name",
        "last_name",
        "status",
        "last_login_at",
        "username",
    }
)


def validate_password(password: str) -> str:
    if len(password) < 12:
        raise UserValidationError("Password must be at least 12 characters.")
    if not re.search(r"[A-Z]", password):
        raise UserValidationError("Password must include an uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise UserValidationError("Password must include a lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise UserValidationError("Password must include a number.")
    if not _PASSWORD_SPECIAL.search(password):
        raise UserValidationError("Password must include a special character.")
    return password


def validate_name(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if len(cleaned) < 2 or len(cleaned) > 100:
        raise UserValidationError(f"{field} must be 2–100 characters.")
    return cleaned


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str | None) -> str | None:
    if username is None:
        return None
    cleaned = username.strip()
    if not cleaned:
        return None
    if not _USERNAME_RE.match(cleaned):
        raise UserValidationError(
            "Username must be 3–100 characters (letters, numbers, . _ -).",
        )
    return cleaned.lower()


def validate_avatar_url(url: str | None) -> str | None:
    if url is None:
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme != "https" or not parsed.netloc:
        raise UserValidationError("avatar_url must be an HTTPS URL or storage path.")
    return cleaned


def validate_sort_by(sort_by: str) -> str:
    if sort_by not in SORT_FIELDS:
        raise UserValidationError(f"Invalid sort_by. Allowed: {', '.join(sorted(SORT_FIELDS))}")
    return sort_by
