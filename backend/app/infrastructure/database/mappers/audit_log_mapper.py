"""Map audit_logs ORM rows to domain entities."""

from __future__ import annotations

from app.domain.entities.audit_log import AuditLog
from app.infrastructure.database.models.audit_log import AuditLogModel


def audit_log_to_entity(model: AuditLogModel) -> AuditLog:
    return AuditLog(
        audit_log_id=int(model.audit_log_id),
        company_id=int(model.company_id),
        actor_user_id=int(model.actor_user_id) if model.actor_user_id is not None else None,
        action=model.action,
        entity_type=model.entity_type,
        entity_id=int(model.entity_id) if model.entity_id is not None else None,
        description=model.description,
        metadata=dict(model.metadata_ or {}),
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        audit_uuid=model.audit_uuid,
        created_at=model.created_at,
    )
