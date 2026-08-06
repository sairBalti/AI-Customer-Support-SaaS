"""Shared request actor / tenant context."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RequestActor:
    """Authenticated caller identity used across modules."""

    user_id: int | None = None
    company_id: int | None = None
    is_super_admin: bool = False
    role_name: str | None = None
    email: str | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, permission: str) -> bool:
        if self.is_super_admin:
            return True
        return permission in self.permissions

    def has_all_permissions(self, *permissions: str) -> bool:
        if self.is_super_admin:
            return True
        return frozenset(permissions).issubset(self.permissions)
