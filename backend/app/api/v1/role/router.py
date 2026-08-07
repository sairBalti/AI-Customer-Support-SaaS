"""Role Management API router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.api.deps import DbSession, RoleServiceDep
from app.api.security import (
    RequireRoleCreate,
    RequireRoleDelete,
    RequireRoleRead,
    RequireRoleUpdate,
)
from app.api.v1.role.schemas import (
    RoleCreateRequest,
    RoleResponse,
    RoleStatusUpdateRequest,
    RoleUpdateRequest,
)
from app.application.dto.role import CreateRoleInput, RoleListQuery, UpdateRoleInput
from app.application.use_cases.role import (
    CreateRoleUseCase,
    GetRoleUseCase,
    ListRolesUseCase,
    RestoreRoleUseCase,
    SetRoleActiveUseCase,
    SoftDeleteRoleUseCase,
    UpdateRoleUseCase,
)
from app.core.pagination import Page
from app.core.responses.envelopes import success_envelope
from app.domain.entities.role import Role

router = APIRouter(prefix="/roles", tags=["Roles"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
}


def _to_response(role: Role) -> dict[str, Any]:
    return RoleResponse.from_entity(role).model_dump(mode="json")


async def _apply_update(
    *,
    role_id: int,
    body: RoleUpdateRequest,
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleUpdate,
) -> dict[str, Any]:
    role = await UpdateRoleUseCase(session, service).execute(
        role_id,
        UpdateRoleInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(role), message="Role updated.")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description=(
        "Hybrid roles: omit `company_id` for global (Super Admin only). "
        "Company Admin creates roles for their own company. "
        "System roles and reserved role names require Super Admin."
    ),
    responses={**_AUTH_RESPONSES, 409: {"description": "Role name conflict"}},
)
async def create_role(
    body: RoleCreateRequest,
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleCreate,
) -> dict[str, Any]:
    role = await CreateRoleUseCase(session, service).execute(
        CreateRoleInput(**body.model_dump()),
        actor,
    )
    return success_envelope(_to_response(role), message="Role created.")


@router.get(
    "",
    summary="List roles",
    description="Tenant sees global + own company roles. Super Admin may filter by company_id.",
    responses=_AUTH_RESPONSES,
)
async def list_roles(
    service: RoleServiceDep,
    actor: RequireRoleRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    company_id: Annotated[int | None, Query(ge=1)] = None,
    include_global: Annotated[bool, Query()] = True,
    is_system_role: Annotated[bool | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "sort_order",
    sort_order: Annotated[str, Query(pattern="^(?i)(asc|desc)$")] = "asc",
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    items, total = await ListRolesUseCase(service).execute(
        RoleListQuery(
            page=page,
            page_size=page_size,
            search=search,
            company_id=company_id,
            include_global=include_global,
            is_system_role=is_system_role,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order.lower(),
            include_deleted=include_deleted,
        ),
        actor,
    )
    page_data = Page.of(
        [_to_response(item) for item in items],
        page=page,
        page_size=page_size,
        total_items=total,
    )
    return success_envelope(page_data.model_dump(mode="json"))


@router.get(
    "/{role_id}",
    summary="Get role by ID",
    responses={**_AUTH_RESPONSES, 404: {"description": "Role not found"}},
)
async def get_role(
    role_id: Annotated[int, Path(ge=1)],
    service: RoleServiceDep,
    actor: RequireRoleRead,
) -> dict[str, Any]:
    role = await GetRoleUseCase(service).execute(role_id, actor)
    return success_envelope(_to_response(role))


@router.put(
    "/{role_id}",
    summary="Update role metadata",
    responses=_AUTH_RESPONSES,
)
async def put_role(
    role_id: Annotated[int, Path(ge=1)],
    body: RoleUpdateRequest,
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleUpdate,
) -> dict[str, Any]:
    return await _apply_update(
        role_id=role_id,
        body=body,
        session=session,
        service=service,
        actor=actor,
    )


@router.patch(
    "/{role_id}",
    summary="Patch role metadata",
    description="Partial update of role fields (same body as PUT).",
    responses=_AUTH_RESPONSES,
)
async def patch_role(
    role_id: Annotated[int, Path(ge=1)],
    body: RoleUpdateRequest,
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleUpdate,
) -> dict[str, Any]:
    return await _apply_update(
        role_id=role_id,
        body=body,
        session=session,
        service=service,
        actor=actor,
    )


@router.patch(
    "/{role_id}/status",
    summary="Activate or deactivate role",
    responses=_AUTH_RESPONSES,
)
async def update_role_status(
    role_id: Annotated[int, Path(ge=1)],
    body: RoleStatusUpdateRequest,
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleUpdate,
) -> dict[str, Any]:
    role = await SetRoleActiveUseCase(session, service).execute(
        role_id,
        is_active=body.is_active,
        actor=actor,
    )
    return success_envelope(_to_response(role), message="Role status updated.")


@router.delete(
    "/{role_id}",
    summary="Soft-delete role",
    description=(
        "Forbidden for system roles, roles assigned to users, " "or roles with permission mappings."
    ),
    responses=_AUTH_RESPONSES,
)
async def delete_role(
    role_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleDelete,
) -> dict[str, Any]:
    role = await SoftDeleteRoleUseCase(session, service).execute(role_id, actor)
    return success_envelope(_to_response(role), message="Role soft-deleted.")


@router.patch(
    "/{role_id}/restore",
    summary="Restore soft-deleted role",
    responses=_AUTH_RESPONSES,
)
async def restore_role(
    role_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: RoleServiceDep,
    actor: RequireRoleUpdate,
) -> dict[str, Any]:
    role = await RestoreRoleUseCase(session, service).execute(role_id, actor)
    return success_envelope(_to_response(role), message="Role restored.")
