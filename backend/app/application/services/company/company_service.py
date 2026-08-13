"""Company application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.context import RequestActor
from app.application.dto.company import (
    CompanyListQuery,
    CreateCompanyInput,
    UpdateCompanyInput,
    UpdateCompanyStatusInput,
    UpdateSubscriptionInput,
)
from app.application.services.company.company_lifecycle import assert_status_transition
from app.application.services.company.company_rules import (
    PLAN_QUOTAS,
    normalize_email,
    normalize_website,
    slugify,
    validate_phone,
    validate_slug,
    validate_sort_by,
)
from app.core.security.rbac import ensure_permissions
from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.company import (
    CompanyAccessDeniedError,
    CompanyConflictError,
    CompanyInactiveError,
    CompanyNotFoundError,
    CompanyValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.user_repository import UserRepository
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.domain.enums.user_status import UserStatus
from app.application.services.user.user_rules import validate_name, validate_password
from app.core.security.password import hash_password


_CLEARABLE_FIELDS = frozenset(
    {
        "legal_name",
        "phone",
        "website",
        "logo_url",
        "industry",
        "country",
    }
)


class CompanyService:
    """Application service containing company business rules."""

    def __init__(
        self,
        repository: CompanyRepository,
        audit_logger: AuditLogger,
        users: UserRepository | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit_logger
        self._users = users
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        """Persist queued audit events on the current session before commit."""
        if not self._pending_audits:
            return
        events = list(self._pending_audits)
        for event in events:
            await self._audit.log(**event)
        self._pending_audits.clear()

    def discard_audits(self) -> None:
        """Drop deferred audits after a failed transaction."""
        self._pending_audits.clear()

    async def create_company(
        self,
        data: CreateCompanyInput,
        actor: RequestActor,
    ) -> Company:
        name = data.company_name.strip()
        if len(name) < 3 or len(name) > 150:
            raise CompanyValidationError("Company name must be 3–150 characters.")

        # Public/self-service onboarding cannot self-assign paid plans.
        plan = data.subscription_plan
        activate_trial = data.activate_trial
        if not actor.is_super_admin:
            plan = SubscriptionPlan.FREE
            activate_trial = True

        slug = validate_slug(data.company_slug) if data.company_slug else slugify(name)
        timezone = self._validate_timezone(data.timezone)
        phone = validate_phone(data.phone)
        website = normalize_website(data.website)
        email = normalize_email(data.email)

        await self._ensure_unique(name=name, slug=slug, email=email)

        quotas = PLAN_QUOTAS[plan]
        trial_ends_at = None
        status = CompanyStatus.ACTIVE
        if activate_trial and plan == SubscriptionPlan.FREE:
            status = CompanyStatus.TRIAL
            trial_ends_at = datetime.now(UTC) + timedelta(days=14)

        payload = {
            "company_name": name,
            "company_slug": slug,
            "legal_name": data.legal_name.strip() if data.legal_name else None,
            "email": email,
            "phone": phone,
            "website": website,
            "logo_url": data.logo_url,
            "industry": data.industry,
            "country": data.country,
            "timezone": timezone,
            "subscription_plan": plan,
            "max_users": quotas["max_users"],
            "max_documents": quotas["max_documents"],
            "max_storage_mb": quotas["max_storage_mb"],
            "monthly_ai_tokens": quotas["monthly_ai_tokens"],
            "token_usage": 0,
            "status": status,
            "trial_ends_at": trial_ends_at,
            "last_activity_at": datetime.now(UTC),
        }
        company = await self._repository.create(payload)
        await self._provision_company_admin(company, data, actor)
        self._queue_audit(
            action="COMPANY_CREATED",
            entity_id=company.company_id,
            company_id=company.company_id,
            user_id=actor.user_id,
            metadata={"slug": company.company_slug, "plan": company.subscription_plan.value},
        )
        return company

    async def _provision_company_admin(
        self,
        company: Company,
        data: CreateCompanyInput,
        actor: RequestActor,
    ) -> None:
        """Create the first Company Admin for public self-service registration."""
        password = (data.admin_password or "").strip() or None
        if actor.is_super_admin and not password:
            return
        if not password:
            raise CompanyValidationError(
                "Admin password is required to create your sign-in account.",
            )
        if self._users is None:
            raise CompanyValidationError("Unable to provision admin user.")

        existing = await self._users.get_by_email(company.email)
        if existing is not None:
            raise CompanyConflictError("A user with this email already exists.")

        role_id = await self._users.get_role_id_by_name("COMPANY_ADMIN")
        if role_id is None:
            raise CompanyValidationError("COMPANY_ADMIN role is not configured.")

        first_name = validate_name(data.admin_first_name or "Company", field="first_name")
        last_name = validate_name(data.admin_last_name or "Admin", field="last_name")
        validate_password(password)
        now = datetime.now(UTC)
        admin = await self._users.create(
            {
                "company_id": company.company_id,
                "role_id": role_id,
                "email": company.email,
                "password_hash": hash_password(password),
                "first_name": first_name,
                "last_name": last_name,
                "display_name": f"{first_name} {last_name}",
                "language": "en",
                "timezone": company.timezone or "UTC",
                "status": UserStatus.ACTIVE,
                "is_email_verified": True,
                "must_change_password": False,
                "password_changed_at": now,
                "failed_login_attempts": 0,
            }
        )
        self._queue_audit(
            action="USER_CREATED",
            entity_id=admin.user_id,
            company_id=company.company_id,
            user_id=actor.user_id,
            metadata={"email": admin.email, "role": "COMPANY_ADMIN", "source": "company_onboarding"},
        )

    async def get_company(self, company_id: int, actor: RequestActor) -> Company:
        ensure_permissions(actor, "companies.read")
        self._assert_tenant_access(company_id, actor)
        company = await self._repository.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError()
        self._assert_company_operational_for_tenant(company, actor)
        return company

    async def list_companies(
        self,
        query: CompanyListQuery,
        actor: RequestActor,
    ) -> tuple[list[Company], int]:
        ensure_permissions(actor, "companies.read")
        tenant_filter: int | None = None
        if not actor.is_super_admin:
            if actor.company_id is None:
                raise CompanyAccessDeniedError()
            tenant_filter = actor.company_id
            await self._assert_actor_company_operational(actor)

        if query.page < 1:
            raise CompanyValidationError("page must be >= 1")
        if query.page_size < 1 or query.page_size > 100:
            raise CompanyValidationError("page_size must be between 1 and 100")

        sort_by = validate_sort_by(query.sort_by)
        sort_order = query.sort_order.lower()
        if sort_order not in {"asc", "desc"}:
            raise CompanyValidationError("sort_order must be 'asc' or 'desc'")

        return await self._repository.search(
            search=query.search,
            status=query.status,
            subscription_plan=query.subscription_plan,
            company_id=tenant_filter,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=query.include_deleted and actor.is_super_admin,
        )

    async def update_company(
        self,
        company_id: int,
        data: UpdateCompanyInput,
        actor: RequestActor,
    ) -> Company:
        ensure_permissions(actor, "companies.update")
        self._assert_tenant_access(company_id, actor)
        existing = await self._repository.get_by_id(company_id)
        if existing is None:
            raise CompanyNotFoundError()
        self._assert_company_operational_for_tenant(existing, actor)

        updates: dict[str, Any] = {}
        values = data.values

        if "company_name" in values and values["company_name"] is not None:
            name = str(values["company_name"]).strip()
            if len(name) < 3 or len(name) > 150:
                raise CompanyValidationError("Company name must be 3–150 characters.")
            conflict = await self._repository.get_by_name(name)
            if conflict and conflict.company_id != company_id:
                raise CompanyConflictError("Company name already exists.")
            updates["company_name"] = name

        if "email" in values and values["email"] is not None:
            email = normalize_email(str(values["email"]))
            conflict = await self._repository.get_by_email(email)
            if conflict and conflict.company_id != company_id:
                raise CompanyConflictError("Company email already exists.")
            updates["email"] = email

        for clearable in _CLEARABLE_FIELDS:
            if clearable not in values:
                continue
            raw = values[clearable]
            if clearable == "phone":
                updates["phone"] = validate_phone(raw)
            elif clearable == "website":
                updates["website"] = normalize_website(raw)
            elif clearable == "legal_name":
                updates["legal_name"] = (
                    raw.strip() if isinstance(raw, str) and raw.strip() else None
                )
            else:
                updates[clearable] = raw

        if "timezone" in values and values["timezone"] is not None:
            updates["timezone"] = self._validate_timezone(str(values["timezone"]))

        if not updates:
            return existing

        updated = await self._repository.update(company_id, updates)
        if updated is None:
            raise CompanyNotFoundError()
        self._queue_audit(
            action="COMPANY_UPDATED",
            entity_id=company_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"fields": sorted(updates.keys())},
        )
        return updated

    async def update_status(
        self,
        company_id: int,
        data: UpdateCompanyStatusInput,
        actor: RequestActor,
    ) -> Company:
        self._assert_can_manage_company(company_id, actor)
        existing = await self._repository.get_by_id(company_id, include_deleted=True)
        if existing is None:
            raise CompanyNotFoundError()

        assert_status_transition(existing.status, data.status)

        patch: dict[str, Any] = {"status": data.status}
        if data.status == CompanyStatus.ARCHIVED:
            patch["deleted_at"] = existing.deleted_at or datetime.now(UTC)
        elif existing.deleted_at is not None and data.status in {
            CompanyStatus.ACTIVE,
            CompanyStatus.TRIAL,
            CompanyStatus.SUSPENDED,
        }:
            # Reactivation clears soft-delete marker.
            patch["deleted_at"] = None

        updated = await self._repository.update(company_id, patch, include_deleted=True)
        if updated is None:
            raise CompanyNotFoundError()
        self._queue_audit(
            action="COMPANY_STATUS_CHANGED",
            entity_id=company_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"from": existing.status.value, "to": data.status.value},
        )
        return updated

    async def update_subscription(
        self,
        company_id: int,
        data: UpdateSubscriptionInput,
        actor: RequestActor,
    ) -> Company:
        self._assert_can_manage_company(company_id, actor)
        existing = await self._repository.get_by_id(company_id)
        if existing is None:
            raise CompanyNotFoundError()

        quotas = PLAN_QUOTAS[data.subscription_plan]
        max_users = data.max_users if data.max_users is not None else quotas["max_users"]
        max_documents = (
            data.max_documents if data.max_documents is not None else quotas["max_documents"]
        )
        max_storage_mb = (
            data.max_storage_mb if data.max_storage_mb is not None else quotas["max_storage_mb"]
        )
        monthly_ai_tokens = (
            data.monthly_ai_tokens
            if data.monthly_ai_tokens is not None
            else quotas["monthly_ai_tokens"]
        )
        if min(max_users, max_documents, max_storage_mb) < 1:
            raise CompanyValidationError("Quota values must be >= 1.")
        if monthly_ai_tokens < 0:
            raise CompanyValidationError("monthly_ai_tokens must be >= 0.")

        updated = await self._repository.update_subscription(
            company_id,
            subscription_plan=data.subscription_plan,
            max_users=max_users,
            max_documents=max_documents,
            max_storage_mb=max_storage_mb,
            monthly_ai_tokens=monthly_ai_tokens,
            subscription_expires_at=data.subscription_expires_at,
        )
        if updated is None:
            raise CompanyNotFoundError()
        self._queue_audit(
            action="COMPANY_SUBSCRIPTION_CHANGED",
            entity_id=company_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={
                "from": existing.subscription_plan.value,
                "to": data.subscription_plan.value,
            },
        )
        return updated

    async def soft_delete_company(self, company_id: int, actor: RequestActor) -> Company:
        """Soft-delete — Super Admin or Company Admin (manage + tenant). Never hard-delete."""
        self._assert_can_manage_company(company_id, actor)
        existing = await self._repository.get_by_id(company_id)
        if existing is None:
            raise CompanyNotFoundError()
        deleted = await self._repository.soft_delete(company_id)
        if deleted is None:
            raise CompanyNotFoundError()
        self._queue_audit(
            action="COMPANY_SOFT_DELETED",
            entity_id=company_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"previous_status": existing.status.value},
        )
        return deleted

    def enforce_user_quota(self, company: Company, current_users: int) -> None:
        if current_users >= company.max_users:
            raise CompanyValidationError("Company user quota exceeded.")

    def enforce_document_quota(self, company: Company, current_documents: int) -> None:
        if current_documents >= company.max_documents:
            raise CompanyValidationError("Company document quota exceeded.")

    def calculate_remaining_tokens(self, company: Company) -> int:
        return max(company.monthly_ai_tokens - company.token_usage, 0)

    def _queue_audit(
        self,
        *,
        action: str,
        entity_id: int,
        company_id: int | None,
        user_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._pending_audits.append(
            {
                "action": action,
                "entity": "companies",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )

    async def _ensure_unique(self, *, name: str, slug: str, email: str) -> None:
        if await self._repository.get_by_name(name):
            raise CompanyConflictError("Company name already exists.")
        if await self._repository.get_by_slug(slug):
            raise CompanyConflictError("Company slug already exists.")
        if await self._repository.get_by_email(email):
            raise CompanyConflictError("Company email already exists.")

    @staticmethod
    def _assert_tenant_access(company_id: int, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.company_id != company_id:
            raise CompanyAccessDeniedError()

    @staticmethod
    def _assert_can_manage_company(company_id: int, actor: RequestActor) -> None:
        """Admin ops: Super Admin (any tenant) or companies.manage within own tenant."""
        ensure_permissions(actor, "companies.manage")
        if actor.is_super_admin:
            return
        if actor.company_id != company_id:
            raise CompanyAccessDeniedError()

    _ACTIVE_STATUSES = frozenset({CompanyStatus.ACTIVE, CompanyStatus.TRIAL})

    def _assert_company_operational_for_tenant(
        self,
        company: Company,
        actor: RequestActor,
    ) -> None:
        if actor.is_super_admin:
            return
        if company.status not in self._ACTIVE_STATUSES:
            raise CompanyInactiveError()

    async def _assert_actor_company_operational(self, actor: RequestActor) -> None:
        if actor.is_super_admin or actor.company_id is None:
            return
        company = await self._repository.get_by_id(actor.company_id)
        if company is None or company.status not in self._ACTIVE_STATUSES:
            raise CompanyInactiveError()

    @staticmethod
    def _validate_timezone(timezone: str) -> str:
        value = timezone.strip() or "UTC"
        if value.upper() == "UTC":
            return "UTC"
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise CompanyValidationError(f"Invalid IANA timezone: {value}") from exc
        return value
