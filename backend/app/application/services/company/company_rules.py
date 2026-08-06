"""Company slug helpers, quotas, and field validators."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.company import CompanyValidationError

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LIKE_ESCAPE_RE = re.compile(r"([%_\\])")

SORTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "created_at",
        "updated_at",
        "company_name",
        "status",
        "subscription_plan",
        "last_activity_at",
        "subscription_expires_at",
    }
)

PLAN_QUOTAS: dict[SubscriptionPlan, dict[str, int]] = {
    SubscriptionPlan.FREE: {
        "max_users": 5,
        "max_documents": 50,
        "max_storage_mb": 500,
        "monthly_ai_tokens": 100_000,
    },
    SubscriptionPlan.STARTER: {
        "max_users": 10,
        "max_documents": 200,
        "max_storage_mb": 2_000,
        "monthly_ai_tokens": 250_000,
    },
    SubscriptionPlan.PRO: {
        "max_users": 25,
        "max_documents": 500,
        "max_storage_mb": 10_000,
        "monthly_ai_tokens": 500_000,
    },
    SubscriptionPlan.BUSINESS: {
        "max_users": 100,
        "max_documents": 2_000,
        "max_storage_mb": 50_000,
        "monthly_ai_tokens": 2_000_000,
    },
    SubscriptionPlan.ENTERPRISE: {
        "max_users": 1_000,
        "max_documents": 50_000,
        "max_storage_mb": 500_000,
        "monthly_ai_tokens": 20_000_000,
    },
}


def slugify(value: str) -> str:
    """Generate a lowercase hyphen-separated slug from a display name."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if not cleaned or not _SLUG_RE.fullmatch(cleaned):
        raise CompanyValidationError("Unable to generate a valid company slug.")
    return cleaned


def validate_slug(slug: str) -> str:
    """Validate an explicit slug value."""
    candidate = slug.strip().lower()
    if not _SLUG_RE.fullmatch(candidate):
        raise CompanyValidationError(
            "Slug must be lowercase, hyphen-separated, and contain no spaces.",
        )
    return candidate


def validate_phone(phone: str | None) -> str | None:
    """Optional phone; E.164 preferred when provided."""
    if phone is None or phone == "":
        return None
    value = phone.strip()
    if not _E164_RE.fullmatch(value):
        raise CompanyValidationError("Phone must use E.164 format (e.g. +15551234567).")
    return value


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if not _EMAIL_RE.fullmatch(value):
        raise CompanyValidationError("Invalid email address.")
    return value


def normalize_website(website: str | None) -> str | None:
    """Optional website; prefer https:// and reject clearly invalid values."""
    if website is None or website == "":
        return None
    value = website.strip()
    if not (value.startswith("https://") or value.startswith("http://")):
        value = f"https://{value}"
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or " " in value
        or "." not in host
    ):
        raise CompanyValidationError("Website must be a valid http(s) URL.")
    return value


def escape_like(term: str) -> str:
    """Escape LIKE wildcards for safe contains search."""
    return _LIKE_ESCAPE_RE.sub(r"\\\1", term)


def validate_sort_by(sort_by: str) -> str:
    if sort_by not in SORTABLE_FIELDS:
        raise CompanyValidationError(
            f"Invalid sort_by '{sort_by}'. Allowed: {', '.join(sorted(SORTABLE_FIELDS))}.",
        )
    return sort_by
