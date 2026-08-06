"""Role field validation helpers."""

from __future__ import annotations

import re

from app.domain.exceptions.role import RoleOperationForbiddenError, RoleValidationError

_ROLE_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,99}$")

# Seeded / platform role names — company tenants must not clone these.
RESERVED_SYSTEM_ROLE_NAMES = frozenset(
    {
        "SUPER_ADMIN",
        "COMPANY_ADMIN",
        "SUPPORT_MANAGER",
        "SUPPORT_AGENT",
        "CUSTOMER",
    }
)

SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "role_name",
        "display_name",
        "sort_order",
        "is_active",
    }
)


def normalize_role_name(value: str) -> str:
    cleaned = value.strip().upper().replace(" ", "_").replace("-", "_")
    if not _ROLE_NAME_RE.match(cleaned):
        raise RoleValidationError(
            "role_name must be uppercase letters/numbers/underscores (e.g. SUPPORT_LEAD).",
        )
    return cleaned


def assert_role_name_allowed_for_actor(
    role_name: str,
    *,
    is_super_admin: bool,
    company_scoped: bool,
) -> None:
    """Prevent privilege escalation via reserved role names."""
    if role_name == "SUPER_ADMIN" and not is_super_admin:
        raise RoleOperationForbiddenError(
            "Company Admin cannot create or assign a Super Admin role.",
        )
    if company_scoped and role_name in RESERVED_SYSTEM_ROLE_NAMES and not is_super_admin:
        raise RoleOperationForbiddenError(
            f"Role name '{role_name}' is reserved for platform system roles.",
        )


def validate_display_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 150:
        raise RoleValidationError("display_name must be 1–150 characters.")
    return cleaned


def validate_description(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 1000:
        raise RoleValidationError("description must be at most 1000 characters.")
    return cleaned


def validate_sort_by(sort_by: str) -> str:
    if sort_by not in SORT_FIELDS:
        raise RoleValidationError(f"Invalid sort_by. Allowed: {', '.join(sorted(SORT_FIELDS))}")
    return sort_by


def validate_sort_order(sort_order: str) -> str:
    normalized = sort_order.lower()
    if normalized not in {"asc", "desc"}:
        raise RoleValidationError("sort_order must be 'asc' or 'desc'")
    return normalized
