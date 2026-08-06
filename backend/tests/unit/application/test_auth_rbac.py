"""Unit tests for RBAC permission helpers."""

import pytest

from app.api.decorators.permissions import permissions
from app.application.context import RequestActor
from app.core.security.rbac import ensure_permissions
from app.domain.exceptions.auth import InsufficientPermissionError, TokenInvalidError


def test_ensure_permissions_allows_matching() -> None:
    actor = RequestActor(
        user_id=1,
        company_id=1,
        permissions=frozenset({"companies.read", "companies.update"}),
    )
    assert ensure_permissions(actor, "companies.read") is actor


def test_ensure_permissions_denies_missing() -> None:
    actor = RequestActor(user_id=1, company_id=1, permissions=frozenset({"companies.read"}))
    with pytest.raises(InsufficientPermissionError):
        ensure_permissions(actor, "companies.manage")


def test_ensure_permissions_requires_auth() -> None:
    with pytest.raises(TokenInvalidError):
        ensure_permissions(RequestActor(), "companies.read")


def test_ensure_permissions_super_admin_without_user_id() -> None:
    actor = RequestActor(is_super_admin=True)
    assert ensure_permissions(actor, "companies.manage") is actor


def test_permissions_decorator_sets_attribute() -> None:
    @permissions("companies.manage")
    async def endpoint() -> None:
        return None

    assert endpoint.permissions == ("companies.manage",)  # type: ignore[attr-defined]
