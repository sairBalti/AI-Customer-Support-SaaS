"""SQLAlchemy Role repository — reuses existing RoleModel."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.role import Role
from app.domain.interfaces.repositories.role_repository import RoleRepository
from app.infrastructure.database.mappers.role_mapper import role_to_entity
from app.infrastructure.database.models.auth import RoleModel, RolePermissionModel, UserModel

_SORTABLE = {
    "created_at": RoleModel.created_at,
    "updated_at": RoleModel.updated_at,
    "role_name": RoleModel.role_name,
    "display_name": RoleModel.display_name,
    "sort_order": RoleModel.sort_order,
    "is_active": RoleModel.is_active,
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> Role:
        model = RoleModel(**data)
        self._session.add(model)
        await self._session.flush()
        return role_to_entity(model)

    async def get_by_id(
        self,
        role_id: int,
        *,
        include_deleted: bool = False,
    ) -> Role | None:
        stmt = select(RoleModel).where(RoleModel.role_id == role_id)
        if not include_deleted:
            stmt = stmt.where(RoleModel.deleted_at.is_(None))
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return role_to_entity(model) if model else None

    async def get_by_name(
        self,
        role_name: str,
        *,
        company_id: int | None = None,
        include_deleted: bool = False,
    ) -> Role | None:
        name = role_name.upper()
        stmt = select(RoleModel).where(RoleModel.role_name == name)
        if company_id is None:
            stmt = stmt.where(RoleModel.company_id.is_(None))
        else:
            stmt = stmt.where(RoleModel.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(RoleModel.deleted_at.is_(None))
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return role_to_entity(model) if model else None

    async def update(
        self,
        role_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Role | None:
        existing = await self.get_by_id(role_id, include_deleted=include_deleted)
        if existing is None:
            return None
        await self._session.execute(
            update(RoleModel).where(RoleModel.role_id == role_id).values(**data)
        )
        await self._session.flush()
        return await self.get_by_id(role_id, include_deleted=True if "deleted_at" in data else include_deleted)

    async def soft_delete(self, role_id: int, *, at: datetime) -> Role | None:
        await self.update(role_id, {"deleted_at": at, "is_active": False})
        return await self.get_by_id(role_id, include_deleted=True)

    async def restore(self, role_id: int) -> Role | None:
        return await self.update(
            role_id,
            {"deleted_at": None, "is_active": True},
            include_deleted=True,
        )

    async def search(
        self,
        *,
        search: str | None,
        company_id: int | None,
        include_global: bool,
        is_system_role: bool | None,
        is_active: bool | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[Role], int]:
        stmt = select(RoleModel)
        count_stmt = select(func.count()).select_from(RoleModel)

        if not include_deleted:
            stmt = stmt.where(RoleModel.deleted_at.is_(None))
            count_stmt = count_stmt.where(RoleModel.deleted_at.is_(None))

        if company_id is not None and include_global:
            scope = or_(RoleModel.company_id == company_id, RoleModel.company_id.is_(None))
            stmt = stmt.where(scope)
            count_stmt = count_stmt.where(scope)
        elif company_id is not None:
            stmt = stmt.where(RoleModel.company_id == company_id)
            count_stmt = count_stmt.where(RoleModel.company_id == company_id)
        elif not include_global:
            # Super Admin listing only company roles when include_global=False and no filter
            stmt = stmt.where(RoleModel.company_id.is_not(None))
            count_stmt = count_stmt.where(RoleModel.company_id.is_not(None))

        if is_system_role is not None:
            stmt = stmt.where(RoleModel.is_system_role.is_(is_system_role))
            count_stmt = count_stmt.where(RoleModel.is_system_role.is_(is_system_role))
        if is_active is not None:
            stmt = stmt.where(RoleModel.is_active.is_(is_active))
            count_stmt = count_stmt.where(RoleModel.is_active.is_(is_active))
        if search:
            pattern = f"%{_escape_like(search.strip())}%"
            filt = or_(
                RoleModel.role_name.ilike(pattern, escape="\\"),
                RoleModel.display_name.ilike(pattern, escape="\\"),
                RoleModel.description.ilike(pattern, escape="\\"),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        col = _SORTABLE.get(sort_by, RoleModel.sort_order)
        order = col.asc() if sort_order.lower() == "asc" else col.desc()
        stmt = stmt.order_by(order, RoleModel.role_id.asc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [role_to_entity(m) for m in rows], total

    async def count_users_with_role(self, role_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.role_id == role_id)
            .where(UserModel.deleted_at.is_(None))
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_role_permissions(self, role_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(RolePermissionModel)
            .where(RolePermissionModel.role_id == role_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())
