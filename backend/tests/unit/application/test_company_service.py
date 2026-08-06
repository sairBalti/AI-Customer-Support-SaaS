"""Unit tests for CompanyService with an in-memory repository double."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.company import (
    CreateCompanyInput,
    UpdateCompanyInput,
    UpdateCompanyStatusInput,
)
from app.application.services.company.company_service import CompanyService
from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.company import (
    CompanyAccessDeniedError,
    CompanyConflictError,
    CompanyNotFoundError,
    CompanyValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.services.audit_logger import AuditLogger


class InMemoryCompanyRepository(CompanyRepository):
    def __init__(self) -> None:
        self._rows: dict[int, Company] = {}
        self._seq = 1

    async def create(self, data: dict[str, Any]) -> Company:
        company_id = self._seq
        self._seq += 1
        now = datetime.now(UTC)
        company = Company(
            company_id=company_id,
            company_name=data["company_name"],
            company_slug=data["company_slug"],
            email=data["email"],
            timezone=data.get("timezone", "UTC"),
            subscription_plan=data["subscription_plan"],
            status=data["status"],
            max_users=data["max_users"],
            max_documents=data["max_documents"],
            max_storage_mb=data["max_storage_mb"],
            monthly_ai_tokens=data["monthly_ai_tokens"],
            token_usage=data.get("token_usage", 0),
            created_at=now,
            updated_at=now,
            legal_name=data.get("legal_name"),
            phone=data.get("phone"),
            website=data.get("website"),
            logo_url=data.get("logo_url"),
            industry=data.get("industry"),
            country=data.get("country"),
            trial_ends_at=data.get("trial_ends_at"),
            subscription_expires_at=data.get("subscription_expires_at"),
            last_activity_at=data.get("last_activity_at"),
            deleted_at=None,
        )
        self._rows[company_id] = company
        return company

    async def get_by_id(self, company_id: int, *, include_deleted: bool = False) -> Company | None:
        company = self._rows.get(company_id)
        if company is None:
            return None
        if company.deleted_at and not include_deleted:
            return None
        return company

    async def get_by_slug(self, company_slug: str, *, include_deleted: bool = False) -> Company | None:
        for company in self._rows.values():
            if company.company_slug == company_slug and (include_deleted or not company.deleted_at):
                return company
        return None

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> Company | None:
        for company in self._rows.values():
            if company.email == email and (include_deleted or not company.deleted_at):
                return company
        return None

    async def get_by_name(self, company_name: str, *, include_deleted: bool = False) -> Company | None:
        for company in self._rows.values():
            if company.company_name == company_name and (include_deleted or not company.deleted_at):
                return company
        return None

    async def update(
        self,
        company_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        company = await self.get_by_id(company_id, include_deleted=include_deleted)
        if company is None:
            return None
        payload = asdict(company)
        payload.update(data)
        payload["updated_at"] = datetime.now(UTC)
        updated = Company(**payload)
        self._rows[company_id] = updated
        return updated

    async def update_subscription(
        self,
        company_id: int,
        *,
        subscription_plan: SubscriptionPlan,
        max_users: int,
        max_documents: int,
        max_storage_mb: int,
        monthly_ai_tokens: int,
        subscription_expires_at: Any | None,
    ) -> Company | None:
        return await self.update(
            company_id,
            {
                "subscription_plan": subscription_plan,
                "max_users": max_users,
                "max_documents": max_documents,
                "max_storage_mb": max_storage_mb,
                "monthly_ai_tokens": monthly_ai_tokens,
                "subscription_expires_at": subscription_expires_at,
            },
        )

    async def update_usage(self, company_id: int, token_usage: int) -> Company | None:
        return await self.update(company_id, {"token_usage": token_usage})

    async def soft_delete(self, company_id: int) -> Company | None:
        return await self.update(
            company_id,
            {"deleted_at": datetime.now(UTC), "status": CompanyStatus.INACTIVE},
        )

    async def archive(self, company_id: int) -> Company | None:
        return await self.update(
            company_id,
            {"deleted_at": datetime.now(UTC), "status": CompanyStatus.ARCHIVED},
            include_deleted=True,
        )

    async def list_active(self) -> list[Company]:
        return [
            c
            for c in self._rows.values()
            if c.deleted_at is None and c.status == CompanyStatus.ACTIVE
        ]

    async def search(self, **kwargs: Any) -> tuple[list[Company], int]:
        items = [c for c in self._rows.values() if c.deleted_at is None]
        company_id = kwargs.get("company_id")
        if company_id is not None:
            items = [c for c in items if c.company_id == company_id]
        return items, len(items)


class RecordingAuditLogger(AuditLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


@pytest.fixture
def service() -> tuple[CompanyService, InMemoryCompanyRepository, RecordingAuditLogger]:
    repo = InMemoryCompanyRepository()
    audit = RecordingAuditLogger()
    return CompanyService(repo, audit), repo, audit


@pytest.mark.asyncio
async def test_create_company_generates_slug_and_audit(service) -> None:
    svc, _repo, audit = service
    actor = RequestActor(is_super_admin=True)
    company = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        actor,
    )
    await svc.flush_audits()
    assert company.company_slug == "acme-corporation"
    assert company.status == CompanyStatus.TRIAL
    assert company.subscription_plan == SubscriptionPlan.FREE
    assert audit.events[-1]["action"] == "COMPANY_CREATED"


@pytest.mark.asyncio
async def test_non_admin_cannot_self_assign_enterprise(service) -> None:
    svc, _, _ = service
    company = await svc.create_company(
        CreateCompanyInput(
            company_name="Acme Corporation",
            email="admin@acme.com",
            subscription_plan=SubscriptionPlan.ENTERPRISE,
            activate_trial=False,
        ),
        RequestActor(is_super_admin=False),
    )
    assert company.subscription_plan == SubscriptionPlan.FREE
    assert company.status == CompanyStatus.TRIAL


@pytest.mark.asyncio
async def test_create_company_conflict(service) -> None:
    svc, _, _ = service
    actor = RequestActor(is_super_admin=True)
    await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        actor,
    )
    with pytest.raises(CompanyConflictError):
        await svc.create_company(
            CreateCompanyInput(company_name="Acme Corporation", email="other@acme.com"),
            actor,
        )


@pytest.mark.asyncio
async def test_tenant_isolation_on_get(service) -> None:
    svc, _, _ = service
    admin = RequestActor(is_super_admin=True)
    created = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        admin,
    )
    tenant = RequestActor(
        user_id=2,
        company_id=999,
        permissions=frozenset({"companies.read"}),
    )
    with pytest.raises(CompanyAccessDeniedError):
        await svc.get_company(created.company_id, tenant)


@pytest.mark.asyncio
async def test_update_company_not_found(service) -> None:
    svc, _, _ = service
    with pytest.raises(CompanyNotFoundError):
        await svc.update_company(
            123,
            UpdateCompanyInput(values={"company_name": "Nope"}),
            RequestActor(is_super_admin=True),
        )


@pytest.mark.asyncio
async def test_update_can_clear_nullable_fields(service) -> None:
    svc, _, _ = service
    actor = RequestActor(is_super_admin=True)
    created = await svc.create_company(
        CreateCompanyInput(
            company_name="Acme Corporation",
            email="admin@acme.com",
            phone="+15551234567",
            website="https://acme.com",
        ),
        actor,
    )
    updated = await svc.update_company(
        created.company_id,
        UpdateCompanyInput(values={"phone": None, "website": None}),
        actor,
    )
    assert updated.phone is None
    assert updated.website is None


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(service) -> None:
    svc, _, _ = service
    actor = RequestActor(is_super_admin=True)
    created = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        actor,
    )
    await svc.update_status(
        created.company_id,
        UpdateCompanyStatusInput(status=CompanyStatus.ARCHIVED),
        actor,
    )
    with pytest.raises(CompanyValidationError):
        await svc.update_status(
            created.company_id,
            UpdateCompanyStatusInput(status=CompanyStatus.ACTIVE),
            actor,
        )
