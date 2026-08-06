"""Reusable security dependency helpers for protected routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import CurrentActorDep, require_permissions
from app.application.context import RequestActor

# Alias matching PRD / task wording ("CurrentUser").
# CurrentActorDep already depends on HTTPBearer → Swagger Authorize lock.
CurrentUserDep = CurrentActorDep

RequireCompanyRead = Annotated[
    RequestActor,
    Depends(require_permissions("companies.read")),
]
RequireCompanyUpdate = Annotated[
    RequestActor,
    Depends(require_permissions("companies.update")),
]
RequireCompanyManage = Annotated[
    RequestActor,
    Depends(require_permissions("companies.manage")),
]

RequireUserCreate = Annotated[
    RequestActor,
    Depends(require_permissions("users.create")),
]
RequireUserRead = Annotated[
    RequestActor,
    Depends(require_permissions("users.read")),
]
RequireUserUpdate = Annotated[
    RequestActor,
    Depends(require_permissions("users.update")),
]
RequireUserDelete = Annotated[
    RequestActor,
    Depends(require_permissions("users.delete")),
]

RequireRoleCreate = Annotated[
    RequestActor,
    Depends(require_permissions("roles.create")),
]
RequireRoleRead = Annotated[
    RequestActor,
    Depends(require_permissions("roles.read")),
]
RequireRoleUpdate = Annotated[
    RequestActor,
    Depends(require_permissions("roles.update")),
]
RequireRoleDelete = Annotated[
    RequestActor,
    Depends(require_permissions("roles.delete")),
]


def secured(*permissions: str) -> list:
    """Optional route-level permission dependencies."""
    if not permissions:
        return []
    return [Depends(require_permissions(*permissions))]
