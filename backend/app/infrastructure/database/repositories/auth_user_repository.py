"""Auth-oriented user repository adapter."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import AuthUser
from app.domain.interfaces.repositories.auth_user_repository import AuthUserRepository
from app.infrastructure.database.mappers.auth_mapper import user_to_auth_entity
from app.infrastructure.database.models.auth import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
)


class SQLAlchemyAuthUserRepository(AuthUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> AuthUser | None:
        stmt = (
            select(UserModel, RoleModel.role_name)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.email == email.lower())
            .where(UserModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        user, role_name = row
        permissions = await self.get_permissions_for_role(int(user.role_id))
        return user_to_auth_entity(user, role_name=role_name, permissions=permissions)

    async def get_by_id(self, user_id: int) -> AuthUser | None:
        stmt = (
            select(UserModel, RoleModel.role_name)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.user_id == user_id)
            .where(UserModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        user, role_name = row
        permissions = await self.get_permissions_for_role(int(user.role_id))
        return user_to_auth_entity(user, role_name=role_name, permissions=permissions)

    async def get_permissions_for_role(self, role_id: int) -> frozenset[str]:
        stmt = (
            select(PermissionModel.permission_name)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.permission_id,
            )
            .where(RolePermissionModel.role_id == role_id)
            .where(PermissionModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return frozenset(result.scalars().all())

    async def record_login_success(
        self,
        user_id: int,
        *,
        ip_address: str | None,
        at: datetime,
    ) -> None:
        await self._session.execute(
            update(UserModel)
            .where(UserModel.user_id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=None,
                last_login_at=at,
                last_login_ip=ip_address,
                updated_at=at,
            )
        )

    async def record_login_failure(
        self,
        user_id: int,
        *,
        failed_login_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        values: dict = {
            "failed_login_attempts": failed_login_attempts,
            "locked_until": locked_until,
        }
        from app.domain.enums.user_status import UserStatus

        if locked_until is not None:
            values["status"] = UserStatus.LOCKED
        await self._session.execute(
            update(UserModel).where(UserModel.user_id == user_id).values(**values)
        )
