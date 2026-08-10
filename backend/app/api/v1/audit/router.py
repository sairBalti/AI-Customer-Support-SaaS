"""Read-only audit log API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import AuditLogServiceDep, DbSession
from app.api.security import RequireAuditRead
from app.api.v1.audit.schemas import AuditLogResponse
from app.application.dto.audit import AuditListQuery
from app.application.use_cases.audit import GetAuditLogUseCase, ListAuditLogsUseCase
from app.core.responses.envelopes import success_envelope
from app.domain.entities.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
    404: {"description": "Audit log not found"},
}


def _to_response(row: AuditLog) -> dict[str, Any]:
    return AuditLogResponse(
        audit_log_id=row.audit_log_id,
        company_id=row.company_id,
        actor_user_id=row.actor_user_id,
        audit_uuid=row.audit_uuid,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        description=row.description,
        metadata=dict(row.metadata or {}),
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        created_at=row.created_at,
    ).model_dump(mode="json")


@router.get(
    "",
    summary="List audit logs",
    description="Paginated company-scoped activity history. Read-only.",
    responses=_AUTH_RESPONSES,
)
async def list_audit_logs(
    session: DbSession,
    service: AuditLogServiceDep,
    actor: RequireAuditRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    actor_user_id: Annotated[int | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[int | None, Query()] = None,
    from_date: Annotated[datetime | None, Query()] = None,
    to_date: Annotated[datetime | None, Query()] = None,
    company_id: Annotated[int | None, Query()] = None,
    sort_order: Annotated[str, Query()] = "desc",
) -> dict[str, Any]:
    page_result = await ListAuditLogsUseCase(session, service).execute(
        AuditListQuery(
            page=page,
            page_size=page_size,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            from_date=from_date,
            to_date=to_date,
            company_id=company_id,
            sort_order=sort_order,
        ),
        actor,
    )
    return success_envelope(
        {
            "items": [_to_response(item) for item in page_result.items],
            "meta": page_result.meta.model_dump(mode="json"),
        }
    )


@router.get(
    "/{audit_log_id}",
    summary="Get audit log",
    responses=_AUTH_RESPONSES,
)
async def get_audit_log(
    audit_log_id: int,
    session: DbSession,
    service: AuditLogServiceDep,
    actor: RequireAuditRead,
) -> dict[str, Any]:
    row = await GetAuditLogUseCase(session, service).execute(audit_log_id, actor)
    return success_envelope(_to_response(row))
