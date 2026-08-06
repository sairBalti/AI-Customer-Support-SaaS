"""Map Role ORM → domain entity."""

from __future__ import annotations

from app.domain.entities.role import Role
from app.infrastructure.database.models.auth import RoleModel


def role_to_entity(model: RoleModel) -> Role:
    return Role(
        role_id=int(model.role_id),
        company_id=int(model.company_id) if model.company_id is not None else None,
        role_name=model.role_name,
        display_name=model.display_name,
        description=model.description,
        is_system_role=bool(model.is_system_role),
        is_active=bool(model.is_active),
        sort_order=int(model.sort_order),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )
