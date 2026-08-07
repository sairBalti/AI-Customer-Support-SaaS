"""Unit tests for UserService."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.user import (
    AssignRoleInput,
    CreateUserInput,
    UpdateUserInput,
)
from app.application.services.user.user_service import UserService
from app.domain.entities.company import Company
from app.domain.entities.managed_user import ManagedUser
from app.domain.entities.refresh_token import RefreshToken
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.user import (
    UserAccessDeniedError,
    UserConflictError,
    UserOperationForbiddenError,
    UserValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.interfaces.repositories.user_repository import UserRepository
from app.domain.interfaces.services.audit_logger import AuditLogger


class FakeUsers(UserRepository):
    def __init__(self) -> None:
        self.rows: dict[int, ManagedUser] = {}
        self.hashes: dict[int, str] = {}
        self.roles = {
            1: "SUPER_ADMIN",
            2: "COMPANY_ADMIN",
            3: "SUPPORT_MANAGER",
            4: "SUPPORT_AGENT",
            5: "CUSTOMER",
        }
        self._seq = 1

    async def create(self, data: dict[str, Any]) -> ManagedUser:
        uid = self._seq
        self._seq += 1
        now = datetime.now(UTC)
        self.hashes[uid] = data["password_hash"]
        user = ManagedUser(
            user_id=uid,
            company_id=data["company_id"],
            role_id=data["role_id"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            status=data["status"],
            is_email_verified=data.get("is_email_verified", False),
            failed_login_attempts=0,
            language=data.get("language", "en"),
            timezone=data.get("timezone", "UTC"),
            created_at=now,
            updated_at=now,
            username=data.get("username"),
            employee_id=data.get("employee_id"),
            display_name=data.get("display_name"),
            phone=data.get("phone"),
            avatar_url=data.get("avatar_url"),
            department=data.get("department"),
            job_title=data.get("job_title"),
            must_change_password=data.get("must_change_password", False),
            password_changed_at=data.get("password_changed_at"),
            role_name=self.roles.get(data["role_id"]),
        )
        self.rows[uid] = user
        return user

    async def get_by_id(self, user_id: int, *, include_deleted: bool = False) -> ManagedUser | None:
        user = self.rows.get(user_id)
        if user is None:
            return None
        if user.deleted_at and not include_deleted:
            return None
        return user

    async def get_by_email(
        self, email: str, *, include_deleted: bool = False
    ) -> ManagedUser | None:
        for user in self.rows.values():
            if user.email == email.lower() and (include_deleted or not user.deleted_at):
                return user
        return None

    async def get_by_username(
        self,
        username: str,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        for user in self.rows.values():
            if user.username == username.lower() and (include_deleted or not user.deleted_at):
                return user
        return None

    async def update(
        self,
        user_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        user = await self.get_by_id(user_id, include_deleted=include_deleted)
        if user is None:
            return None
        if "password_hash" in data:
            self.hashes[user_id] = data["password_hash"]
        payload = asdict(user)
        payload.update({k: v for k, v in data.items() if k != "password_hash"})
        if "role_id" in data:
            payload["role_name"] = self.roles.get(data["role_id"])
        payload["updated_at"] = datetime.now(UTC)
        updated = ManagedUser(**payload)
        self.rows[user_id] = updated
        return updated

    async def soft_delete(self, user_id: int, *, at: datetime) -> ManagedUser | None:
        return await self.update(user_id, {"deleted_at": at, "status": UserStatus.INACTIVE})

    async def restore(self, user_id: int) -> ManagedUser | None:
        return await self.update(
            user_id,
            {"deleted_at": None, "status": UserStatus.ACTIVE},
            include_deleted=True,
        )

    async def search(self, **kwargs: Any) -> tuple[list[ManagedUser], int]:
        items = [u for u in self.rows.values() if u.deleted_at is None]
        company_id = kwargs.get("company_id")
        if company_id is not None:
            items = [u for u in items if u.company_id == company_id]
        return items, len(items)

    async def count_by_company(self, company_id: int, *, include_deleted: bool = False) -> int:
        return sum(
            1
            for u in self.rows.values()
            if u.company_id == company_id and (include_deleted or not u.deleted_at)
        )

    async def count_active_company_admins(
        self,
        company_id: int,
        *,
        exclude_user_id: int | None = None,
    ) -> int:
        count = 0
        for u in self.rows.values():
            if u.company_id != company_id or u.deleted_at or u.status != UserStatus.ACTIVE:
                continue
            if u.role_name != "COMPANY_ADMIN":
                continue
            if exclude_user_id is not None and u.user_id == exclude_user_id:
                continue
            count += 1
        return count

    async def get_role_id_by_name(self, role_name: str) -> int | None:
        for rid, name in self.roles.items():
            if name == role_name.upper():
                return rid
        return None

    async def get_role_name(self, role_id: int) -> str | None:
        return self.roles.get(role_id)

    async def get_password_hash(self, user_id: int) -> str | None:
        return self.hashes.get(user_id)


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


class FakeRefresh(RefreshTokenRepository):
    def __init__(self) -> None:
        self.revoked: list[int] = []

    async def create(self, data: dict[str, Any]) -> RefreshToken:
        raise NotImplementedError

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return None

    async def revoke(self, token_id: int, *, at: datetime) -> None:
        return None

    async def revoke_all_for_user(self, user_id: int, *, at: datetime) -> int:
        self.revoked.append(user_id)
        return 1

    async def rotate(
        self, old_token_id: int, new_data: dict[str, Any], *, at: datetime
    ) -> RefreshToken:
        raise NotImplementedError


class FakeAudit(AuditLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def _svc() -> tuple[UserService, FakeUsers, FakeRefresh]:
    users = FakeUsers()
    refresh = FakeRefresh()
    return UserService(users, FakeCompanies(), refresh, FakeAudit()), users, refresh


def _admin() -> RequestActor:
    return RequestActor(
        user_id=100,
        company_id=10,
        is_super_admin=False,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"users.create", "users.read", "users.update", "users.delete"}),
    )


@pytest.mark.asyncio
async def test_create_user_hashes_password() -> None:
    svc, users, _ = _svc()
    created = await svc.create_user(
        CreateUserInput(
            company_id=10,
            email="agent@acme.com",
            password="Str0ng!Password",
            first_name="Al",
            last_name="Agent",
            role_name="SUPPORT_AGENT",
        ),
        _admin(),
    )
    await svc.flush_audits()
    assert created.email == "agent@acme.com"
    assert users.hashes[created.user_id] != "Str0ng!Password"
    assert created.role_name == "SUPPORT_AGENT"


@pytest.mark.asyncio
async def test_duplicate_email_rejected() -> None:
    svc, _, _ = _svc()
    await svc.create_user(
        CreateUserInput(
            company_id=10,
            email="agent@acme.com",
            password="Str0ng!Password",
            first_name="Al",
            last_name="Agent",
            role_name="SUPPORT_AGENT",
        ),
        _admin(),
    )
    with pytest.raises(UserConflictError):
        await svc.create_user(
            CreateUserInput(
                company_id=10,
                email="agent@acme.com",
                password="Str0ng!Password",
                first_name="Other",
                last_name="Agent",
                role_name="SUPPORT_AGENT",
            ),
            _admin(),
        )


@pytest.mark.asyncio
async def test_company_admin_cannot_promote_super_admin() -> None:
    svc, _, _ = _svc()
    with pytest.raises(UserOperationForbiddenError):
        await svc.create_user(
            CreateUserInput(
                company_id=10,
                email="x@acme.com",
                password="Str0ng!Password",
                first_name="Bad",
                last_name="Promo",
                role_name="SUPER_ADMIN",
            ),
            _admin(),
        )


@pytest.mark.asyncio
async def test_cross_tenant_access_denied() -> None:
    svc, users, _ = _svc()
    created = await svc.create_user(
        CreateUserInput(
            company_id=10,
            email="agent@acme.com",
            password="Str0ng!Password",
            first_name="Al",
            last_name="Agent",
            role_name="SUPPORT_AGENT",
        ),
        _admin(),
    )
    outsider = RequestActor(
        user_id=9,
        company_id=999,
        permissions=frozenset({"users.read"}),
    )
    with pytest.raises(UserAccessDeniedError):
        await svc.get_user(created.user_id, outsider)


@pytest.mark.asyncio
async def test_cannot_remove_last_company_admin_role() -> None:
    svc, users, _ = _svc()
    admin_user = await svc.create_user(
        CreateUserInput(
            company_id=10,
            email="admin@acme.com",
            password="Str0ng!Password",
            first_name="Cara",
            last_name="Admin",
            role_name="COMPANY_ADMIN",
        ),
        RequestActor(is_super_admin=True, user_id=1, permissions=frozenset()),
    )
    with pytest.raises(UserOperationForbiddenError):
        await svc.assign_role(
            admin_user.user_id,
            AssignRoleInput(role_name="CUSTOMER"),
            RequestActor(
                user_id=1,
                company_id=10,
                is_super_admin=True,
            ),
        )


@pytest.mark.asyncio
async def test_weak_password_rejected() -> None:
    svc, _, _ = _svc()
    with pytest.raises(UserValidationError):
        await svc.create_user(
            CreateUserInput(
                company_id=10,
                email="w@acme.com",
                password="short",
                first_name="Weak",
                last_name="Pass",
                role_name="CUSTOMER",
            ),
            _admin(),
        )


@pytest.mark.asyncio
async def test_owner_profile_update_ok() -> None:
    svc, users, _ = _svc()
    created = await svc.create_user(
        CreateUserInput(
            company_id=10,
            email="agent@acme.com",
            password="Str0ng!Password",
            first_name="Al",
            last_name="Agent",
            role_name="SUPPORT_AGENT",
        ),
        _admin(),
    )
    owner = RequestActor(user_id=created.user_id, company_id=10, permissions=frozenset())
    updated = await svc.update_user(
        created.user_id,
        UpdateUserInput(values={"display_name": "Al A."}),
        owner,
    )
    assert updated.display_name == "Al A."
