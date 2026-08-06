"""Role Management application service (hybrid global / company roles)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.application.context import RequestActor
from app.application.dto.role import CreateRoleInput, RoleListQuery, UpdateRoleInput
from app.application.services.role.role_rules import (
    assert_role_name_allowed_for_actor,
    normalize_role_name,
    validate_description,
    validate_display_name,
    validate_sort_by,
    validate_sort_order,
)
from app.core.security.rbac import ensure_permissions
from app.domain.entities.role import Role
from app.domain.exceptions.role import (
    RoleAccessDeniedError,
    RoleConflictError,
    RoleNotFoundError,
    RoleOperationForbiddenError,
    RoleValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.role_repository import RoleRepository
from app.domain.interfaces.services.audit_logger import AuditLogger


class RoleService:
    def __init__(
        self,
        roles: RoleRepository,
        companies: CompanyRepository,
        audit_logger: AuditLogger,
    ) -> None:
        self._roles = roles
        self._companies = companies
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        events = list(self._pending_audits)
        self._pending_audits.clear()
        for event in events:
            await self._audit.log(**event)

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def create_role(self, data: CreateRoleInput, actor: RequestActor) -> Role:
        ensure_permissions(actor, "roles.create")

        company_id = data.company_id
        if not actor.is_super_admin:
            if company_id is None:
                company_id = actor.company_id
            if company_id is None:
                raise RoleAccessDeniedError()
            self._assert_tenant_scope(company_id, actor)

        if data.is_system_role and not actor.is_super_admin:
            raise RoleOperationForbiddenError("Only Super Admin can create system roles.")
        if company_id is None and not actor.is_super_admin:
            raise RoleOperationForbiddenError("Only Super Admin can create global roles.")
        if company_id is not None:
            self._assert_tenant_scope(company_id, actor)
            company = await self._companies.get_by_id(company_id)
            if company is None:
                raise RoleValidationError("Company does not exist.")

        role_name = normalize_role_name(data.role_name)
        assert_role_name_allowed_for_actor(
            role_name,
            is_super_admin=actor.is_super_admin,
            company_scoped=company_id is not None,
        )
        display_name = validate_display_name(data.display_name)
        description = validate_description(data.description)
        if data.sort_order < 0:
            raise RoleValidationError("sort_order must be >= 0")

        await self._ensure_unique_name(role_name, company_id=company_id)

        try:
            role = await self._roles.create(
                {
                    "company_id": company_id,
                    "role_name": role_name,
                    "display_name": display_name,
                    "description": description,
                    "is_system_role": bool(data.is_system_role) if actor.is_super_admin else False,
                    "is_active": data.is_active,
                    "sort_order": data.sort_order,
                }
            )
        except IntegrityError as exc:
            raise RoleConflictError("Role name already exists for this scope.") from exc

        self._queue_audit(
            action="ROLE_CREATED",
            entity_id=role.role_id,
            company_id=role.company_id,
            user_id=actor.user_id,
            metadata={"role_name": role.role_name},
        )
        return role

    async def list_roles(
        self,
        query: RoleListQuery,
        actor: RequestActor,
    ) -> tuple[list[Role], int]:
        ensure_permissions(actor, "roles.read")
        if query.page < 1:
            raise RoleValidationError("page must be >= 1")
        if query.page_size < 1 or query.page_size > 100:
            raise RoleValidationError("page_size must be between 1 and 100")

        company_id = query.company_id
        include_global = query.include_global
        if not actor.is_super_admin:
            if actor.company_id is None:
                raise RoleAccessDeniedError()
            if company_id is not None and company_id != actor.company_id:
                raise RoleAccessDeniedError()
            company_id = actor.company_id
            include_global = True

        return await self._roles.search(
            search=query.search,
            company_id=company_id,
            include_global=include_global if company_id is not None else True,
            is_system_role=query.is_system_role,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
            sort_by=validate_sort_by(query.sort_by),
            sort_order=validate_sort_order(query.sort_order),
            include_deleted=query.include_deleted and actor.is_super_admin,
        )

    async def get_role(self, role_id: int, actor: RequestActor) -> Role:
        ensure_permissions(actor, "roles.read")
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()
        self._assert_can_view(role, actor)
        return role

    async def update_role(
        self,
        role_id: int,
        data: UpdateRoleInput,
        actor: RequestActor,
    ) -> Role:
        ensure_permissions(actor, "roles.update")
        existing = await self._require_role(role_id)
        self._assert_can_manage(existing, actor)

        updates: dict[str, Any] = {}
        values = data.values

        if "display_name" in values and values["display_name"] is not None:
            updates["display_name"] = validate_display_name(str(values["display_name"]))
        if "description" in values:
            updates["description"] = validate_description(values["description"])
        if "sort_order" in values and values["sort_order"] is not None:
            sort_order = int(values["sort_order"])
            if sort_order < 0:
                raise RoleValidationError("sort_order must be >= 0")
            updates["sort_order"] = sort_order
        if "is_active" in values and values["is_active"] is not None:
            updates["is_active"] = bool(values["is_active"])

        if "role_name" in values and values["role_name"] is not None:
            if existing.is_system_role:
                raise RoleOperationForbiddenError("System role names are immutable.")
            new_name = normalize_role_name(str(values["role_name"]))
            assert_role_name_allowed_for_actor(
                new_name,
                is_super_admin=actor.is_super_admin,
                company_scoped=existing.company_id is not None,
            )
            if new_name != existing.role_name:
                await self._ensure_unique_name(
                    new_name,
                    company_id=existing.company_id,
                    exclude_role_id=role_id,
                )
            updates["role_name"] = new_name

        if not updates:
            return existing

        try:
            updated = await self._roles.update(role_id, updates)
        except IntegrityError as exc:
            raise RoleConflictError("Role name already exists for this scope.") from exc
        if updated is None:
            raise RoleNotFoundError()
        self._queue_audit(
            action="ROLE_UPDATED",
            entity_id=role_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={"fields": sorted(updates.keys())},
        )
        return updated

    async def soft_delete_role(self, role_id: int, actor: RequestActor) -> Role:
        ensure_permissions(actor, "roles.delete")
        existing = await self._require_role(role_id)
        self._assert_can_manage(existing, actor)
        if existing.is_system_role:
            raise RoleOperationForbiddenError("System roles cannot be deleted.")
        users = await self._roles.count_users_with_role(role_id)
        if users > 0:
            raise RoleOperationForbiddenError(
                "Role cannot be deleted while assigned to users.",
            )
        mappings = await self._roles.count_role_permissions(role_id)
        if mappings > 0:
            raise RoleOperationForbiddenError(
                "Role cannot be deleted while permission mappings exist.",
            )
        deleted = await self._roles.soft_delete(role_id, at=datetime.now(UTC))
        if deleted is None:
            raise RoleNotFoundError()
        self._queue_audit(
            action="ROLE_SOFT_DELETED",
            entity_id=role_id,
            company_id=existing.company_id,
            user_id=actor.user_id,
            metadata={},
        )
        return deleted

    async def restore_role(self, role_id: int, actor: RequestActor) -> Role:
        ensure_permissions(actor, "roles.update")
        existing = await self._roles.get_by_id(role_id, include_deleted=True)
        if existing is None:
            raise RoleNotFoundError()
        self._assert_can_manage(existing, actor)
        restored = await self._roles.restore(role_id)
        if restored is None:
            raise RoleNotFoundError()
        self._queue_audit(
            action="ROLE_RESTORED",
            entity_id=role_id,
            company_id=restored.company_id,
            user_id=actor.user_id,
            metadata={},
        )
        return restored

    async def set_active(self, role_id: int, *, is_active: bool, actor: RequestActor) -> Role:
        return await self.update_role(
            role_id,
            UpdateRoleInput(values={"is_active": is_active}),
            actor,
        )

    async def _require_role(self, role_id: int) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()
        return role

    async def _ensure_unique_name(
        self,
        role_name: str,
        *,
        company_id: int | None,
        exclude_role_id: int | None = None,
    ) -> None:
        existing = await self._roles.get_by_name(
            role_name,
            company_id=company_id,
            include_deleted=True,
        )
        if existing and existing.role_id != exclude_role_id:
            scope = "platform" if company_id is None else f"company {company_id}"
            raise RoleConflictError(f"Role name already exists for this {scope}.")

    def _assert_tenant_scope(self, company_id: int, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.company_id != company_id:
            raise RoleAccessDeniedError()

    def _assert_can_view(self, role: Role, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if role.is_global:
            return
        if actor.company_id == role.company_id:
            return
        raise RoleAccessDeniedError()

    def _assert_can_manage(self, role: Role, actor: RequestActor) -> None:
        if role.is_system_role and not actor.is_super_admin:
            raise RoleOperationForbiddenError("Company Admin cannot modify system roles.")
        if role.is_global and not actor.is_super_admin:
            raise RoleOperationForbiddenError("Only Super Admin can manage global roles.")
        if role.company_id is not None:
            self._assert_tenant_scope(role.company_id, actor)

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
                "entity": "roles",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
