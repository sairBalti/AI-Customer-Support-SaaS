"""User Management use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.application.services.user.user_service import UserService
from app.domain.entities.managed_user import ManagedUser


class _MutatingUseCase:
    def __init__(self, session: AsyncSession, service: UserService) -> None:
        self._session = session
        self._service = service

    async def _commit(self, result: ManagedUser) -> ManagedUser:
        try:
            await self._service.flush_audits()
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        return result

    async def _run(self, coro) -> ManagedUser:
        try:
            result = await coro
            await self._service.flush_audits()
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        return result


class CreateUserUseCase(_MutatingUseCase):
    async def execute(self, data: CreateUserInput, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.create_user(data, actor))


class UpdateUserUseCase(_MutatingUseCase):
    async def execute(
        self,
        user_id: int,
        data: UpdateUserInput,
        actor: RequestActor,
    ) -> ManagedUser:
        return await self._run(self._service.update_user(user_id, data, actor))


class UpdateProfileUseCase(_MutatingUseCase):
    async def execute(self, data: UpdateProfileInput, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.update_profile(data, actor))


class SoftDeleteUserUseCase(_MutatingUseCase):
    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.soft_delete_user(user_id, actor))


class RestoreUserUseCase(_MutatingUseCase):
    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.restore_user(user_id, actor))


class ActivateUserUseCase(_MutatingUseCase):
    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.activate_user(user_id, actor))


class DeactivateUserUseCase(_MutatingUseCase):
    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.deactivate_user(user_id, actor))


class ChangePasswordUseCase(_MutatingUseCase):
    async def execute(
        self,
        user_id: int,
        data: ChangePasswordInput,
        actor: RequestActor,
    ) -> ManagedUser:
        return await self._run(self._service.change_password(user_id, data, actor))


class ResetPasswordUseCase(_MutatingUseCase):
    async def execute(
        self,
        user_id: int,
        data: ResetPasswordInput,
        actor: RequestActor,
    ) -> ManagedUser:
        return await self._run(self._service.reset_password(user_id, data, actor))


class AssignRoleUseCase(_MutatingUseCase):
    async def execute(
        self,
        user_id: int,
        data: AssignRoleInput,
        actor: RequestActor,
    ) -> ManagedUser:
        return await self._run(self._service.assign_role(user_id, data, actor))


class RemoveRoleUseCase(_MutatingUseCase):
    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._run(self._service.remove_role(user_id, actor))


class AssignCompanyUseCase(_MutatingUseCase):
    async def execute(
        self,
        user_id: int,
        data: AssignCompanyInput,
        actor: RequestActor,
    ) -> ManagedUser:
        return await self._run(self._service.assign_company(user_id, data, actor))


class ListUsersUseCase:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def execute(
        self,
        query: UserListQuery,
        actor: RequestActor,
    ) -> tuple[list[ManagedUser], int]:
        return await self._service.list_users(query, actor)


class GetUserUseCase:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def execute(self, user_id: int, actor: RequestActor) -> ManagedUser:
        return await self._service.get_user(user_id, actor)


class GetMyProfileUseCase:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def execute(self, actor: RequestActor) -> ManagedUser:
        return await self._service.get_me(actor)
