"""Unit tests for RoleService (hybrid company / global roles)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.role import CreateRoleInput, UpdateRoleInput
from app.application.services.role.role_service import RoleService
from app.domain.entities.company import Company
from app.domain.entities.role import Role
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.role import (
    RoleConflictError,
    RoleOperationForbiddenError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.role_repository import RoleRepository
from app.domain.interfaces.services.audit_logger import AuditLogger


class FakeRoles(RoleRepository):
    def __init__(self) -> None:
        self.rows: dict[int, Role] = {}
        self.user_counts: dict[int, int] = {}
        self.perm_counts: dict[int, int] = {}
        self._seq = 1

    async def create(self, data: dict[str, Any]) -> Role:
        rid = self._seq
        self._seq += 1
        now = datetime.now(UTC)
        role = Role(
            role_id=rid,
            company_id=data.get("company_id"),
            role_name=data["role_name"],
            display_name=data["display_name"],
            description=data.get("description"),
            is_system_role=data.get("is_system_role", False),
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
            created_at=now,
            updated_at=now,
        )
        self.rows[rid] = role
        return role

    async def get_by_id(self, role_id: int, *, include_deleted: bool = False) -> Role | None:
        role = self.rows.get(role_id)
        if role is None:
            return None
        if role.deleted_at and not include_deleted:
            return None
        return role

    async def get_by_name(
        self,
        role_name: str,
        *,
        company_id: int | None = None,
        include_deleted: bool = False,
    ) -> Role | None:
        for role in self.rows.values():
            if role.role_name != role_name.upper():
                continue
            if role.company_id != company_id:
                continue
            if role.deleted_at and not include_deleted:
                continue
            return role
        return None

    async def update(
        self,
        role_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Role | None:
        role = await self.get_by_id(role_id, include_deleted=include_deleted)
        if role is None:
            return None
        payload = asdict(role)
        payload.update(data)
        payload["updated_at"] = datetime.now(UTC)
        updated = Role(**payload)
        self.rows[role_id] = updated
        return updated

    async def soft_delete(self, role_id: int, *, at: datetime) -> Role | None:
        return await self.update(role_id, {"deleted_at": at, "is_active": False})

    async def restore(self, role_id: int) -> Role | None:
        return await self.update(
            role_id,
            {"deleted_at": None, "is_active": True},
            include_deleted=True,
        )

    async def search(self, **kwargs: Any) -> tuple[list[Role], int]:
        items = [r for r in self.rows.values() if r.deleted_at is None]
        return items, len(items)

    async def count_users_with_role(self, role_id: int) -> int:
        return self.user_counts.get(role_id, 0)

    async def count_role_permissions(self, role_id: int) -> int:
        return self.perm_counts.get(role_id, 0)


class FakeCompanies(CompanyRepository):
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.company = Company(
            company_id=10,
            company_name="Acme",
            company_slug="acme",
            email="ops@acme.com",
            timezone="UTC",
            subscription_plan=SubscriptionPlan.FREE,
            status=CompanyStatus.ACTIVE,
            max_users=5,
            max_documents=50,
            max_storage_mb=500,
            monthly_ai_tokens=100000,
            token_usage=0,
            created_at=now,
            updated_at=now,
        )

    async def create(self, data: dict[str, Any]) -> Company:
        raise NotImplementedError

    async def get_by_id(self, company_id: int, *, include_deleted: bool = False) -> Company | None:
        return self.company if company_id == 10 else None

    async def get_by_slug(
        self, company_slug: str, *, include_deleted: bool = False
    ) -> Company | None:
        return None

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> Company | None:
        return None

    async def get_by_name(
        self, company_name: str, *, include_deleted: bool = False
    ) -> Company | None:
        return None

    async def update(
        self, company_id: int, data: dict[str, Any], *, include_deleted: bool = False
    ) -> Company | None:
        return None

    async def update_subscription(self, *args: Any, **kwargs: Any) -> Company | None:
        return None

    async def update_usage(self, company_id: int, token_usage: int) -> Company | None:
        return None

    async def soft_delete(self, company_id: int) -> Company | None:
        return None

    async def archive(self, company_id: int) -> Company | None:
        return None

    async def list_active(self) -> list[Company]:
        return [self.company]

    async def search(self, **kwargs: Any) -> tuple[list[Company], int]:
        return [self.company], 1


class FakeAudit(AuditLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def _svc() -> tuple[RoleService, FakeRoles]:
    roles = FakeRoles()
    return RoleService(roles, FakeCompanies(), FakeAudit()), roles


def _company_admin() -> RequestActor:
    return RequestActor(
        user_id=1,
        company_id=10,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"roles.create", "roles.read", "roles.update", "roles.delete"}),
    )


def _super() -> RequestActor:
    return RequestActor(user_id=99, company_id=1, is_super_admin=True)


@pytest.mark.asyncio
async def test_company_admin_creates_company_role() -> None:
    svc, _ = _svc()
    role = await svc.create_role(
        CreateRoleInput(role_name="support_lead", display_name="Support Lead"),
        _company_admin(),
    )
    assert role.company_id == 10
    assert role.role_name == "SUPPORT_LEAD"
    assert role.is_system_role is False


@pytest.mark.asyncio
async def test_same_role_name_allowed_across_companies() -> None:
    svc, roles = _svc()
    await svc.create_role(
        CreateRoleInput(role_name="LEAD", display_name="Lead A", company_id=10),
        _super(),
    )
    # Simulate another company id without FakeCompanies entry by super creating with company 10 twice would conflict
    await roles.create(
        {
            "company_id": 20,
            "role_name": "LEAD",
            "display_name": "Lead B",
            "is_system_role": False,
            "is_active": True,
            "sort_order": 0,
        }
    )
    found = await roles.get_by_name("LEAD", company_id=20)
    assert found is not None
    assert found.display_name == "Lead B"


@pytest.mark.asyncio
async def test_duplicate_name_within_company_rejected() -> None:
    svc, _ = _svc()
    await svc.create_role(
        CreateRoleInput(role_name="LEAD", display_name="Lead", company_id=10),
        _company_admin(),
    )
    with pytest.raises(RoleConflictError):
        await svc.create_role(
            CreateRoleInput(role_name="LEAD", display_name="Lead 2", company_id=10),
            _company_admin(),
        )


@pytest.mark.asyncio
async def test_company_admin_cannot_modify_system_role() -> None:
    svc, roles = _svc()
    system = await roles.create(
        {
            "company_id": None,
            "role_name": "COMPANY_ADMIN",
            "display_name": "Company Admin",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 1,
        }
    )
    with pytest.raises(RoleOperationForbiddenError):
        await svc.update_role(
            system.role_id,
            UpdateRoleInput(values={"display_name": "Hacked"}),
            _company_admin(),
        )


@pytest.mark.asyncio
async def test_cannot_delete_role_with_users() -> None:
    svc, roles = _svc()
    role = await svc.create_role(
        CreateRoleInput(role_name="TEMP", display_name="Temp", company_id=10),
        _company_admin(),
    )
    roles.user_counts[role.role_id] = 3
    with pytest.raises(RoleOperationForbiddenError):
        await svc.soft_delete_role(role.role_id, _company_admin())


@pytest.mark.asyncio
async def test_cannot_delete_role_with_permission_mappings() -> None:
    svc, roles = _svc()
    role = await svc.create_role(
        CreateRoleInput(role_name="MAPPED", display_name="Mapped", company_id=10),
        _company_admin(),
    )
    roles.perm_counts[role.role_id] = 2
    with pytest.raises(RoleOperationForbiddenError):
        await svc.soft_delete_role(role.role_id, _company_admin())


@pytest.mark.asyncio
async def test_company_admin_cannot_create_super_admin_named_role() -> None:
    svc, _ = _svc()
    with pytest.raises(RoleOperationForbiddenError):
        await svc.create_role(
            CreateRoleInput(role_name="SUPER_ADMIN", display_name="Nope", company_id=10),
            _company_admin(),
        )


@pytest.mark.asyncio
async def test_system_roles_only_super_admin() -> None:
    svc, _ = _svc()
    with pytest.raises(RoleOperationForbiddenError):
        await svc.create_role(
            CreateRoleInput(
                role_name="PLATFORM_OPS",
                display_name="Ops",
                is_system_role=True,
            ),
            _company_admin(),
        )
    role = await svc.create_role(
        CreateRoleInput(
            role_name="PLATFORM_OPS",
            display_name="Ops",
            is_system_role=True,
        ),
        _super(),
    )
    assert role.is_global
    assert role.is_system
