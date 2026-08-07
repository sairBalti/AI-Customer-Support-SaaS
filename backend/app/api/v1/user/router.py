"""User Management API router.

Register ``/me`` routes before ``/{user_id}`` path params.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUserDep, DbSession, UserServiceDep
from app.api.security import (
    RequireUserCreate,
    RequireUserDelete,
    RequireUserRead,
    RequireUserUpdate,
)
from app.api.v1.user.schemas import (
    AssignCompanyRequest,
    AssignRolesRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    UserCreateRequest,
    UserProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)
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
from app.application.use_cases.user import (
    ActivateUserUseCase,
    AssignCompanyUseCase,
    AssignRoleUseCase,
    ChangePasswordUseCase,
    CreateUserUseCase,
    DeactivateUserUseCase,
    GetMyProfileUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    RemoveRoleUseCase,
    ResetPasswordUseCase,
    RestoreUserUseCase,
    SoftDeleteUserUseCase,
    UpdateProfileUseCase,
    UpdateUserUseCase,
)
from app.core.pagination import Page
from app.core.responses.envelopes import success_envelope
from app.domain.entities.managed_user import ManagedUser
from app.domain.enums.user_status import UserStatus

router = APIRouter(prefix="/users", tags=["Users"])


def _to_response(user: ManagedUser) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Requires `users.create`. Company Admin limited to own company.",
    responses={401: {"description": "Unauthenticated"}, 403: {"description": "Forbidden"}},
)
async def create_user(
    body: UserCreateRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserCreate,
) -> dict[str, Any]:
    user = await CreateUserUseCase(session, service).execute(
        CreateUserInput(**body.model_dump()),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User created.")


@router.get(
    "",
    summary="List users",
    description="Requires `users.read`. Tenant-scoped for Company Admin.",
)
async def list_users(
    service: UserServiceDep,
    actor: RequireUserRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    status_filter: Annotated[UserStatus | None, Query(alias="status")] = None,
    role_id: Annotated[int | None, Query(ge=1)] = None,
    company_id: Annotated[int | None, Query(ge=1)] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query(pattern="^(?i)(asc|desc)$")] = "desc",
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    items, total = await ListUsersUseCase(service).execute(
        UserListQuery(
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
            role_id=role_id,
            company_id=company_id,
            sort_by=sort_by,
            sort_order=sort_order.lower(),
            include_deleted=include_deleted,
        ),
        actor,
    )
    page_data = Page.of(
        [_to_response(item).model_dump(mode="json") for item in items],
        page=page,
        page_size=page_size,
        total_items=total,
    )
    return success_envelope(page_data.model_dump(mode="json"))


@router.get(
    "/me",
    summary="Get my profile",
    description="Requires Bearer JWT. Returns the authenticated user.",
)
async def get_my_profile(
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await GetMyProfileUseCase(service).execute(actor)
    return success_envelope(_to_response(user).model_dump(mode="json"))


@router.put(
    "/me",
    summary="Update my profile",
    description="Owner profile fields only (no role/company/status).",
)
async def update_my_profile(
    body: UserProfileUpdateRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await UpdateProfileUseCase(session, service).execute(
        UpdateProfileInput(**body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="Profile updated.")


@router.get(
    "/{user_id}",
    summary="Get user by ID",
    description="Owner, Company Admin (same tenant), or Super Admin.",
)
async def get_user(
    user_id: Annotated[int, Path(ge=1)],
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await GetUserUseCase(service).execute(user_id, actor)
    return success_envelope(_to_response(user).model_dump(mode="json"))


@router.put(
    "/{user_id}",
    summary="Update user (full/partial via body)",
)
async def put_user(
    user_id: Annotated[int, Path(ge=1)],
    body: UserUpdateRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await UpdateUserUseCase(session, service).execute(
        user_id,
        UpdateUserInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User updated.")


@router.patch(
    "/{user_id}",
    summary="Patch user fields",
)
async def patch_user(
    user_id: Annotated[int, Path(ge=1)],
    body: UserUpdateRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await UpdateUserUseCase(session, service).execute(
        user_id,
        UpdateUserInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User updated.")


@router.delete(
    "/{user_id}",
    summary="Soft-delete user",
    description="Requires `users.delete`. Soft delete only.",
)
async def delete_user(
    user_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserDelete,
) -> dict[str, Any]:
    user = await SoftDeleteUserUseCase(session, service).execute(user_id, actor)
    return success_envelope(
        _to_response(user).model_dump(mode="json"),
        message="User soft-deleted.",
    )


@router.patch(
    "/{user_id}/activate",
    summary="Activate user",
)
async def activate_user(
    user_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await ActivateUserUseCase(session, service).execute(user_id, actor)
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User activated.")


@router.patch(
    "/{user_id}/deactivate",
    summary="Deactivate user",
)
async def deactivate_user(
    user_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await DeactivateUserUseCase(session, service).execute(user_id, actor)
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User deactivated.")


@router.patch(
    "/{user_id}/restore",
    summary="Restore soft-deleted user",
)
async def restore_user(
    user_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await RestoreUserUseCase(session, service).execute(user_id, actor)
    return success_envelope(_to_response(user).model_dump(mode="json"), message="User restored.")


@router.patch(
    "/{user_id}/change-password",
    summary="Change password",
    description="Owner (current password required) or admin updating another user.",
)
async def change_password(
    user_id: Annotated[int, Path(ge=1)],
    body: ChangePasswordRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await ChangePasswordUseCase(session, service).execute(
        user_id,
        ChangePasswordInput(**body.model_dump()),
        actor,
    )
    return success_envelope(
        _to_response(user).model_dump(mode="json"),
        message="Password changed. Refresh tokens revoked.",
    )


@router.patch(
    "/{user_id}/reset-password",
    summary="Force password reset",
    description="Requires `users.update`. Invalidates refresh tokens.",
)
async def reset_password(
    user_id: Annotated[int, Path(ge=1)],
    body: ResetPasswordRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await ResetPasswordUseCase(session, service).execute(
        user_id,
        ResetPasswordInput(**body.model_dump()),
        actor,
    )
    return success_envelope(
        _to_response(user).model_dump(mode="json"),
        message="Password reset. Refresh tokens revoked.",
    )


@router.patch(
    "/{user_id}/roles",
    summary="Assign role",
    description="Single role per user. Company Admin cannot assign SUPER_ADMIN.",
)
async def assign_roles(
    user_id: Annotated[int, Path(ge=1)],
    body: AssignRolesRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await AssignRoleUseCase(session, service).execute(
        user_id,
        AssignRoleInput(**body.model_dump()),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="Role assigned.")


@router.delete(
    "/{user_id}/roles",
    summary="Remove elevated role",
    description="Demotes user to CUSTOMER (single-role model).",
)
async def remove_roles(
    user_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: UserServiceDep,
    actor: RequireUserUpdate,
) -> dict[str, Any]:
    user = await RemoveRoleUseCase(session, service).execute(user_id, actor)
    return success_envelope(_to_response(user).model_dump(mode="json"), message="Role removed.")


@router.patch(
    "/{user_id}/company",
    summary="Assign company",
    description="Super Admin only.",
)
async def assign_company(
    user_id: Annotated[int, Path(ge=1)],
    body: AssignCompanyRequest,
    session: DbSession,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    user = await AssignCompanyUseCase(session, service).execute(
        user_id,
        AssignCompanyInput(company_id=body.company_id),
        actor,
    )
    return success_envelope(_to_response(user).model_dump(mode="json"), message="Company assigned.")
