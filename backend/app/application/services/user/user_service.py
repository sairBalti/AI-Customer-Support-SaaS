"""User Management application service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.application.context import RequestActor
from app.application.dto.user import (
    AssignCompanyInput,
    AssignRoleInput,
    ChangePasswordInput,
    CreateUserInput,
    ResetPasswordInput,
    UpdateProfileInput,
    UpdateUserInput,
    UserListQuery,
)
from app.application.services.user.user_rules import (
    normalize_email,
    normalize_username,
    validate_avatar_url,
    validate_name,
    validate_password,
    validate_sort_by,
)
from app.core.security.password import hash_password, verify_password
from app.core.security.rbac import ensure_permissions
from app.domain.entities.managed_user import ManagedUser
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.user import (
    UserAccessDeniedError,
    UserConflictError,
    UserNotFoundError,
    UserOperationForbiddenError,
    UserValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.interfaces.repositories.user_repository import UserRepository
from app.domain.interfaces.services.audit_logger import AuditLogger

_PROFILE_FIELDS = frozenset(
    {
        "first_name",
        "last_name",
        "display_name",
        "phone",
        "avatar_url",
        "department",
        "job_title",
        "language",
        "timezone",
        "username",
    }
)
_ADMIN_FIELDS = frozenset(
    {
        "email",
        "employee_id",
        "status",
        "is_email_verified",
        "role_id",
        "company_id",
    }
)


class UserService:
    """Business rules for user management (reuses auth hashing + refresh tokens)."""

    def __init__(
        self,
        users: UserRepository,
        companies: CompanyRepository,
        refresh_tokens: RefreshTokenRepository,
        audit_logger: AuditLogger,
    ) -> None:
        self._users = users
        self._companies = companies
        self._refresh_tokens = refresh_tokens
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        events = list(self._pending_audits)
        self._pending_audits.clear()
        for event in events:
            await self._audit.log(**event)

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def create_user(self, data: CreateUserInput, actor: RequestActor) -> ManagedUser:
        ensure_permissions(actor, "users.create")
        company_id = data.company_id
        self._assert_can_manage_company_users(company_id, actor)

        company = await self._companies.get_by_id(company_id)
        if company is None:
            raise UserValidationError("Company does not exist.")

        current_users = await self._users.count_by_company(company_id)
        if current_users >= company.max_users:
            raise UserValidationError("Company user quota exceeded.")

        role_id = await self._resolve_role_id(data.role_id, data.role_name)
        role_name = await self._users.get_role_name(role_id)
        self._assert_can_assign_role(actor, role_name)

        email = normalize_email(data.email)
        username = normalize_username(data.username)
        await self._ensure_unique_email(email)
        if username:
            await self._ensure_unique_username(username)

        validate_password(data.password)
        now = datetime.now(UTC)
        payload = {
            "company_id": company_id,
            "role_id": role_id,
            "email": email,
            "username": username,
            "password_hash": hash_password(data.password),
            "first_name": validate_name(data.first_name, field="first_name"),
            "last_name": validate_name(data.last_name, field="last_name"),
            "display_name": data.display_name.strip() if data.display_name else None,
            "employee_id": data.employee_id,
            "phone": data.phone,
            "avatar_url": validate_avatar_url(data.avatar_url),
            "department": data.department,
            "job_title": data.job_title,
            "language": data.language or "en",
            "timezone": data.timezone or "UTC",
            "status": data.status,
            "is_email_verified": data.is_email_verified,
            "must_change_password": False,
            "password_changed_at": now,
            "failed_login_attempts": 0,
        }
        user = await self._users.create(payload)
        self._queue_audit(
            action="USER_CREATED",
            entity_id=user.user_id,
            company_id=user.company_id,
            user_id=actor.user_id,
            metadata={"email": user.email, "role": user.role_name},
        )
        return user

    async def list_users(
        self,
        query: UserListQuery,
        actor: RequestActor,
    ) -> tuple[list[ManagedUser], int]:
        ensure_permissions(actor, "users.read")
        tenant_filter = self._tenant_filter(actor, query.company_id)
        if query.page < 1:
            raise UserValidationError("page must be >= 1")
        if query.page_size < 1 or query.page_size > 100:
            raise UserValidationError("page_size must be between 1 and 100")
        sort_by = validate_sort_by(query.sort_by)
        sort_order = query.sort_order.lower()
        if sort_order not in {"asc", "desc"}:
            raise UserValidationError("sort_order must be 'asc' or 'desc'")
        return await self._users.search(
            search=query.search,
            status=query.status,
            role_id=query.role_id,
            company_id=tenant_filter,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=query.include_deleted and actor.is_super_admin,
        )

    async def get_user(self, user_id: int, actor: RequestActor) -> ManagedUser:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        self._assert_can_view_user(user, actor)
        return user

    async def get_me(self, actor: RequestActor) -> ManagedUser:
        if actor.user_id is None:
            raise UserAccessDeniedError("Authentication required.")
        user = await self._users.get_by_id(actor.user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def update_user(
        self,
        user_id: int,
        data: UpdateUserInput,
        actor: RequestActor,
    ) -> ManagedUser:
        existing = await self._require_user(user_id)
        self._assert_can_update_user(existing, actor, data.values)

        updates: dict[str, Any] = {}
        values = data.values

        if "first_name" in values and values["first_name"] is not None:
            updates["first_name"] = validate_name(str(values["first_name"]), field="first_name")
        if "last_name" in values and values["last_name"] is not None:
            updates["last_name"] = validate_name(str(values["last_name"]), field="last_name")
        for optional in ("display_name", "phone", "department", "job_title", "employee_id"):
            if optional in values:
                raw = values[optional]
                updates[optional] = raw.strip() if isinstance(raw, str) and raw.strip() else None
        if "avatar_url" in values:
            updates["avatar_url"] = validate_avatar_url(values["avatar_url"])
        if "language" in values and values["language"] is not None:
            updates["language"] = str(values["language"]).strip() or "en"
        if "timezone" in values and values["timezone"] is not None:
            updates["timezone"] = str(values["timezone"]).strip() or "UTC"
        if "username" in values:
            username = normalize_username(values["username"])
            if username and username != existing.username:
                await self._ensure_unique_username(username, exclude_user_id=user_id)
            updates["username"] = username

        is_admin_update = actor.is_super_admin or actor.has_permission("users.update")
        if is_admin_update and not self._is_owner_only(existing, actor):
            if "email" in values and values["email"] is not None:
                email = normalize_email(str(values["email"]))
                if email != existing.email:
                    await self._ensure_unique_email(email, exclude_user_id=user_id)
                updates["email"] = email
            if "status" in values and values["status"] is not None:
                updates["status"] = (
                    values["status"]
                    if isinstance(values["status"], UserStatus)
                    else UserStatus(str(values["status"]))
                )
            if "is_email_verified" in values and values["is_email_verified"] is not None:
                updates["is_email_verified"] = bool(values["is_email_verified"])

        if not updates:
            return existing

        updated = await self._users.update(user_id, updates)
        if updated is None:
            raise UserNotFoundError()
        self._queue_audit(
            action="USER_UPDATED",
            entity_id=user_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={"fields": sorted(updates.keys())},
        )
        return updated

    async def update_profile(
        self,
        data: UpdateProfileInput,
        actor: RequestActor,
    ) -> ManagedUser:
        if actor.user_id is None:
            raise UserAccessDeniedError("Authentication required.")
        values: dict[str, Any] = {}
        for field_name in _PROFILE_FIELDS:
            if not hasattr(data, field_name):
                continue
            val = getattr(data, field_name)
            if val is not None:
                values[field_name] = val
        return await self.update_user(actor.user_id, UpdateUserInput(values=values), actor)

    async def soft_delete_user(self, user_id: int, actor: RequestActor) -> ManagedUser:
        ensure_permissions(actor, "users.delete")
        existing = await self._require_user(user_id)
        self._assert_can_manage_company_users(existing.company_id, actor)
        if actor.user_id == user_id:
            raise UserOperationForbiddenError("You cannot delete your own account.")
        if existing.is_company_admin:
            others = await self._users.count_active_company_admins(
                existing.company_id,
                exclude_user_id=user_id,
            )
            if others == 0:
                raise UserOperationForbiddenError(
                    "Cannot delete the last Company Admin for this company.",
                )
        deleted = await self._users.soft_delete(user_id, at=datetime.now(UTC))
        if deleted is None:
            raise UserNotFoundError()
        await self._refresh_tokens.revoke_all_for_user(user_id, at=datetime.now(UTC))
        self._queue_audit(
            action="USER_SOFT_DELETED",
            entity_id=user_id,
            company_id=existing.company_id,
            user_id=actor.user_id,
            metadata={},
        )
        return deleted

    async def restore_user(self, user_id: int, actor: RequestActor) -> ManagedUser:
        ensure_permissions(actor, "users.update")
        existing = await self._users.get_by_id(user_id, include_deleted=True)
        if existing is None:
            raise UserNotFoundError()
        self._assert_can_manage_company_users(existing.company_id, actor)
        restored = await self._users.restore(user_id)
        if restored is None:
            raise UserNotFoundError()
        self._queue_audit(
            action="USER_RESTORED",
            entity_id=user_id,
            company_id=restored.company_id,
            user_id=actor.user_id,
            metadata={},
        )
        return restored

    async def activate_user(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._set_status(user_id, UserStatus.ACTIVE, actor, action="USER_ACTIVATED")

    async def deactivate_user(self, user_id: int, actor: RequestActor) -> ManagedUser:
        user = await self._set_status(user_id, UserStatus.INACTIVE, actor, action="USER_DEACTIVATED")
        await self._refresh_tokens.revoke_all_for_user(user_id, at=datetime.now(UTC))
        return user

    async def change_password(
        self,
        user_id: int,
        data: ChangePasswordInput,
        actor: RequestActor,
    ) -> ManagedUser:
        existing = await self._require_user(user_id)
        # Owner may change own password; admins need users.update for others.
        if actor.user_id != user_id:
            ensure_permissions(actor, "users.update")
            self._assert_can_manage_company_users(existing.company_id, actor)
        elif actor.user_id is None:
            raise UserAccessDeniedError()

        stored = await self._users.get_password_hash(user_id)
        if stored is None or not verify_password(data.current_password, stored):
            raise UserValidationError("Current password is incorrect.")
        validate_password(data.new_password)
        now = datetime.now(UTC)
        updated = await self._users.update(
            user_id,
            {
                "password_hash": hash_password(data.new_password),
                "password_changed_at": now,
                "must_change_password": False,
            },
        )
        if updated is None:
            raise UserNotFoundError()
        await self._refresh_tokens.revoke_all_for_user(user_id, at=now)
        self._queue_audit(
            action="USER_PASSWORD_CHANGED",
            entity_id=user_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={},
        )
        return updated

    async def reset_password(
        self,
        user_id: int,
        data: ResetPasswordInput,
        actor: RequestActor,
    ) -> ManagedUser:
        ensure_permissions(actor, "users.update")
        existing = await self._require_user(user_id)
        self._assert_can_manage_company_users(existing.company_id, actor)
        validate_password(data.new_password)
        now = datetime.now(UTC)
        updated = await self._users.update(
            user_id,
            {
                "password_hash": hash_password(data.new_password),
                "password_changed_at": now,
                "must_change_password": data.force_change_on_next_login,
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )
        if updated is None:
            raise UserNotFoundError()
        await self._refresh_tokens.revoke_all_for_user(user_id, at=now)
        self._queue_audit(
            action="USER_PASSWORD_RESET",
            entity_id=user_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={"force_change": data.force_change_on_next_login},
        )
        return updated

    async def assign_role(
        self,
        user_id: int,
        data: AssignRoleInput,
        actor: RequestActor,
    ) -> ManagedUser:
        ensure_permissions(actor, "users.update")
        existing = await self._require_user(user_id)
        self._assert_can_manage_company_users(existing.company_id, actor)
        role_id = await self._resolve_role_id(data.role_id, data.role_name)
        role_name = await self._users.get_role_name(role_id)
        self._assert_can_assign_role(actor, role_name)

        if existing.is_company_admin and role_name != "COMPANY_ADMIN":
            others = await self._users.count_active_company_admins(
                existing.company_id,
                exclude_user_id=user_id,
            )
            if others == 0:
                raise UserOperationForbiddenError(
                    "Cannot remove the last Company Admin role for this company.",
                )

        updated = await self._users.update(user_id, {"role_id": role_id})
        if updated is None:
            raise UserNotFoundError()
        self._queue_audit(
            action="USER_ROLE_ASSIGNED",
            entity_id=user_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={"role": role_name, "from": existing.role_name},
        )
        return updated

    async def remove_role(
        self,
        user_id: int,
        actor: RequestActor,
    ) -> ManagedUser:
        """Demote user to CUSTOMER (single-role model — remove elevated role)."""
        return await self.assign_role(
            user_id,
            AssignRoleInput(role_name="CUSTOMER"),
            actor,
        )

    async def assign_company(
        self,
        user_id: int,
        data: AssignCompanyInput,
        actor: RequestActor,
    ) -> ManagedUser:
        if not actor.is_super_admin:
            raise UserOperationForbiddenError("Only Super Admin can assign companies.")
        existing = await self._require_user(user_id)
        company = await self._companies.get_by_id(data.company_id)
        if company is None:
            raise UserValidationError("Target company does not exist.")
        if existing.is_company_admin:
            others = await self._users.count_active_company_admins(
                existing.company_id,
                exclude_user_id=user_id,
            )
            if others == 0:
                raise UserOperationForbiddenError(
                    "Cannot move the last Company Admin to another company.",
                )
        updated = await self._users.update(user_id, {"company_id": data.company_id})
        if updated is None:
            raise UserNotFoundError()
        await self._refresh_tokens.revoke_all_for_user(user_id, at=datetime.now(UTC))
        self._queue_audit(
            action="USER_COMPANY_ASSIGNED",
            entity_id=user_id,
            company_id=data.company_id,
            user_id=actor.user_id,
            metadata={"from": existing.company_id, "to": data.company_id},
        )
        return updated

    # --- helpers ---

    async def _set_status(
        self,
        user_id: int,
        status: UserStatus,
        actor: RequestActor,
        *,
        action: str,
    ) -> ManagedUser:
        ensure_permissions(actor, "users.update")
        existing = await self._require_user(user_id)
        self._assert_can_manage_company_users(existing.company_id, actor)
        if (
            existing.is_company_admin
            and status != UserStatus.ACTIVE
            and actor.user_id != user_id
        ):
            others = await self._users.count_active_company_admins(
                existing.company_id,
                exclude_user_id=user_id,
            )
            if others == 0 and status == UserStatus.INACTIVE:
                raise UserOperationForbiddenError(
                    "Cannot deactivate the last Company Admin for this company.",
                )
        updated = await self._users.update(user_id, {"status": status})
        if updated is None:
            raise UserNotFoundError()
        self._queue_audit(
            action=action,
            entity_id=user_id,
            company_id=updated.company_id,
            user_id=actor.user_id,
            metadata={"status": status.value},
        )
        return updated

    async def _require_user(self, user_id: int) -> ManagedUser:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def _resolve_role_id(self, role_id: int | None, role_name: str | None) -> int:
        if role_id is not None:
            name = await self._users.get_role_name(role_id)
            if name is None:
                raise UserValidationError("Invalid role_id.")
            return role_id
        if role_name:
            resolved = await self._users.get_role_id_by_name(role_name)
            if resolved is None:
                raise UserValidationError(f"Unknown role: {role_name}")
            return resolved
        raise UserValidationError("role_id or role_name is required.")

    async def _ensure_unique_email(self, email: str, *, exclude_user_id: int | None = None) -> None:
        existing = await self._users.get_by_email(email, include_deleted=True)
        if existing and existing.user_id != exclude_user_id:
            raise UserConflictError("Email already exists.")

    async def _ensure_unique_username(
        self,
        username: str,
        *,
        exclude_user_id: int | None = None,
    ) -> None:
        existing = await self._users.get_by_username(username, include_deleted=True)
        if existing and existing.user_id != exclude_user_id:
            raise UserConflictError("Username already exists.")

    def _tenant_filter(self, actor: RequestActor, requested_company_id: int | None) -> int | None:
        if actor.is_super_admin:
            return requested_company_id
        if actor.company_id is None:
            raise UserAccessDeniedError()
        if requested_company_id is not None and requested_company_id != actor.company_id:
            raise UserAccessDeniedError()
        return actor.company_id

    def _assert_can_manage_company_users(self, company_id: int, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.company_id != company_id:
            raise UserAccessDeniedError()

    def _assert_can_view_user(self, user: ManagedUser, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.user_id == user.user_id:
            return
        if actor.has_permission("users.read") and actor.company_id == user.company_id:
            return
        raise UserAccessDeniedError()

    def _assert_can_update_user(
        self,
        user: ManagedUser,
        actor: RequestActor,
        values: dict[str, Any],
    ) -> None:
        if actor.is_super_admin:
            return
        if actor.user_id == user.user_id:
            forbidden = set(values) & _ADMIN_FIELDS
            if forbidden and not actor.has_permission("users.update"):
                raise UserOperationForbiddenError(
                    f"Owners cannot update: {', '.join(sorted(forbidden))}",
                )
            if actor.company_id == user.company_id:
                return
        if actor.has_permission("users.update") and actor.company_id == user.company_id:
            return
        raise UserAccessDeniedError()

    def _is_owner_only(self, user: ManagedUser, actor: RequestActor) -> bool:
        return (
            actor.user_id == user.user_id
            and not actor.is_super_admin
            and not actor.has_permission("users.update")
        )

    def _assert_can_assign_role(self, actor: RequestActor, role_name: str | None) -> None:
        if role_name is None:
            raise UserValidationError("Role not found.")
        if role_name.upper() == "SUPER_ADMIN" and not actor.is_super_admin:
            raise UserOperationForbiddenError(
                "Company Admin cannot promote a user to Super Admin.",
            )

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
                "entity": "users",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
