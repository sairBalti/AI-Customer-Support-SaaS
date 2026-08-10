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

RequireDocumentUpload = Annotated[
    RequestActor,
    Depends(require_permissions("documents.upload")),
]
RequireDocumentRead = Annotated[
    RequestActor,
    Depends(require_permissions("documents.read")),
]
RequireDocumentUpdate = Annotated[
    RequestActor,
    Depends(require_permissions("documents.update")),
]
RequireDocumentDelete = Annotated[
    RequestActor,
    Depends(require_permissions("documents.delete")),
]
RequireDocumentReindex = Annotated[
    RequestActor,
    Depends(require_permissions("documents.reindex")),
]

RequireKnowledgeProcess = Annotated[
    RequestActor,
    Depends(require_permissions("knowledge.process")),
]
RequireKnowledgeSearch = Annotated[
    RequestActor,
    Depends(require_permissions("knowledge.search")),
]

RequireChatStart = Annotated[
    RequestActor,
    Depends(require_permissions("chat.start")),
]
RequireChatRead = Annotated[
    RequestActor,
    Depends(require_permissions("chat.read")),
]

RequireTicketCreate = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.create")),
]
RequireTicketRead = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.read")),
]
RequireTicketUpdate = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.update")),
]
RequireTicketAssign = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.assign")),
]
RequireTicketResolve = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.resolve")),
]
RequireTicketClose = Annotated[
    RequestActor,
    Depends(require_permissions("tickets.close")),
]

RequireAuditRead = Annotated[
    RequestActor,
    Depends(require_permissions("audit.read")),
]


def secured(*permissions: str) -> list:
    """Optional route-level permission dependencies."""
    if not permissions:
        return []
    return [Depends(require_permissions(*permissions))]
