"""User Management SQLAlchemy repository — reuses existing UserModel."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.managed_user import ManagedUser
from app.domain.enums.user_status import UserStatus
from app.domain.interfaces.repositories.user_repository import UserRepository
from app.infrastructure.database.mappers.user_mapper import user_to_managed_entity
from app.infrastructure.database.models.auth import RoleModel, UserModel

_SORTABLE = {
    "created_at": UserModel.created_at,
    "updated_at": UserModel.updated_at,
    "email": UserModel.email,
    "first_name": UserModel.first_name,
    "last_name": UserModel.last_name,
    "status": UserModel.status,
    "last_login_at": UserModel.last_login_at,
    "username": UserModel.username,
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> ManagedUser:
        model = UserModel(**data)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        role_name = await self.get_role_name(int(model.role_id))
        return user_to_managed_entity(model, role_name=role_name)

    async def get_by_id(
        self,
        user_id: int,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        stmt = (
            select(UserModel, RoleModel.role_name)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.user_id == user_id)
        )
        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        model, role_name = row
        return user_to_managed_entity(model, role_name=role_name)

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        stmt = (
            select(UserModel, RoleModel.role_name)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.email == email.lower())
        )
        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        model, role_name = row
        return user_to_managed_entity(model, role_name=role_name)

    async def get_by_username(
        self,
        username: str,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        stmt = (
            select(UserModel, RoleModel.role_name)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.username == username.lower())
        )
        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        model, role_name = row
        return user_to_managed_entity(model, role_name=role_name)

    async def update(
        self,
        user_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        existing = await self.get_by_id(user_id, include_deleted=include_deleted)
        if existing is None:
            return None
        await self._session.execute(
            update(UserModel).where(UserModel.user_id == user_id).values(**data)
        )
        await self._session.flush()
        return await self.get_by_id(user_id, include_deleted=include_deleted)

    async def soft_delete(self, user_id: int, *, at: datetime) -> ManagedUser | None:
        updated = await self.update(
            user_id,
            {"deleted_at": at, "status": UserStatus.INACTIVE},
        )
        if updated is None:
            # update() re-fetches with deleted_at filter; read including deleted.
            return await self.get_by_id(user_id, include_deleted=True)
        return updated

    async def restore(self, user_id: int) -> ManagedUser | None:
        return await self.update(
            user_id,
            {"deleted_at": None, "status": UserStatus.ACTIVE},
            include_deleted=True,
        )

    async def search(
        self,
        *,
        search: str | None,
        status: UserStatus | None,
        role_id: int | None,
        company_id: int | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[ManagedUser], int]:
        stmt = select(UserModel, RoleModel.role_name).join(
            RoleModel,
            RoleModel.role_id == UserModel.role_id,
        )
        count_stmt = select(func.count()).select_from(UserModel)

        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
            count_stmt = count_stmt.where(UserModel.deleted_at.is_(None))
        if company_id is not None:
            stmt = stmt.where(UserModel.company_id == company_id)
            count_stmt = count_stmt.where(UserModel.company_id == company_id)
        if status is not None:
            stmt = stmt.where(UserModel.status == status)
            count_stmt = count_stmt.where(UserModel.status == status)
        if role_id is not None:
            stmt = stmt.where(UserModel.role_id == role_id)
            count_stmt = count_stmt.where(UserModel.role_id == role_id)
        if search:
            pattern = f"%{_escape_like(search.strip())}%"
            filt = or_(
                UserModel.email.ilike(pattern, escape="\\"),
                UserModel.first_name.ilike(pattern, escape="\\"),
                UserModel.last_name.ilike(pattern, escape="\\"),
                UserModel.username.ilike(pattern, escape="\\"),
                UserModel.display_name.ilike(pattern, escape="\\"),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        col = _SORTABLE.get(sort_by, UserModel.created_at)
        order = col.asc() if sort_order.lower() == "asc" else col.desc()
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(stmt)).all()
        items = [user_to_managed_entity(model, role_name=role_name) for model, role_name in rows]
        return items, total

    async def count_by_company(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(UserModel).where(UserModel.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_active_company_admins(
        self,
        company_id: int,
        *,
        exclude_user_id: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .join(RoleModel, RoleModel.role_id == UserModel.role_id)
            .where(UserModel.company_id == company_id)
            .where(UserModel.deleted_at.is_(None))
            .where(UserModel.status == UserStatus.ACTIVE)
            .where(RoleModel.role_name == "COMPANY_ADMIN")
        )
        if exclude_user_id is not None:
            stmt = stmt.where(UserModel.user_id != exclude_user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_role_id_by_name(self, role_name: str) -> int | None:
        """Resolve role by name preferring global system roles."""
        name = role_name.upper()
        # Prefer global (company_id IS NULL), then any non-deleted match.
        stmt_global = (
            select(RoleModel.role_id)
            .where(RoleModel.role_name == name)
            .where(RoleModel.company_id.is_(None))
            .where(RoleModel.deleted_at.is_(None))
            .where(RoleModel.is_active.is_(True))
            .limit(1)
        )
        value = (await self._session.execute(stmt_global)).scalar_one_or_none()
        if value is not None:
            return int(value)
        stmt = (
            select(RoleModel.role_id)
            .where(RoleModel.role_name == name)
            .where(RoleModel.deleted_at.is_(None))
            .where(RoleModel.is_active.is_(True))
            .limit(1)
        )
        value = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(value) if value is not None else None

    async def get_role_name(self, role_id: int) -> str | None:
        result = await self._session.execute(
            select(RoleModel.role_name).where(RoleModel.role_id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_password_hash(self, user_id: int) -> str | None:
        result = await self._session.execute(
            select(UserModel.password_hash).where(UserModel.user_id == user_id)
        )
        value = result.scalar_one_or_none()
        return str(value) if value is not None else None
