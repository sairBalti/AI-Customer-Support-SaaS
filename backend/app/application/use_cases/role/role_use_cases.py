"""Role Management use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.role import CreateRoleInput, RoleListQuery, UpdateRoleInput
from app.application.services.role.role_service import RoleService
from app.domain.entities.role import Role


class _Mutating:
    def __init__(self, session: AsyncSession, service: RoleService) -> None:
        self._session = session
        self._service = service

    async def _run(self, coro) -> Role:
        try:
            result = await coro
            await self._service.flush_audits()
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        return result


class CreateRoleUseCase(_Mutating):
    async def execute(self, data: CreateRoleInput, actor: RequestActor) -> Role:
        return await self._run(self._service.create_role(data, actor))


class UpdateRoleUseCase(_Mutating):
    async def execute(self, role_id: int, data: UpdateRoleInput, actor: RequestActor) -> Role:
        return await self._run(self._service.update_role(role_id, data, actor))


class SoftDeleteRoleUseCase(_Mutating):
    async def execute(self, role_id: int, actor: RequestActor) -> Role:
        return await self._run(self._service.soft_delete_role(role_id, actor))


class RestoreRoleUseCase(_Mutating):
    async def execute(self, role_id: int, actor: RequestActor) -> Role:
        return await self._run(self._service.restore_role(role_id, actor))


class SetRoleActiveUseCase(_Mutating):
    async def execute(self, role_id: int, *, is_active: bool, actor: RequestActor) -> Role:
        return await self._run(self._service.set_active(role_id, is_active=is_active, actor=actor))


class ListRolesUseCase:
    def __init__(self, service: RoleService) -> None:
        self._service = service

    async def execute(
        self,
        query: RoleListQuery,
        actor: RequestActor,
    ) -> tuple[list[Role], int]:
        return await self._service.list_roles(query, actor)


class GetRoleUseCase:
    def __init__(self, service: RoleService) -> None:
        self._service = service

    async def execute(self, role_id: int, actor: RequestActor) -> Role:
        return await self._service.get_role(role_id, actor)
