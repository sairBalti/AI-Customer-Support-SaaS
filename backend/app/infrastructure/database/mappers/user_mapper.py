"""Map User ORM models to ManagedUser entities."""

from __future__ import annotations

from app.domain.entities.managed_user import ManagedUser
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.auth import UserModel


def user_to_managed_entity(
    model: UserModel,
    *,
    role_name: str | None = None,
) -> ManagedUser:
    status = model.status if isinstance(model.status, UserStatus) else UserStatus(str(model.status))
    return ManagedUser(
        user_id=int(model.user_id),
        company_id=int(model.company_id),
        role_id=int(model.role_id),
        username=getattr(model, "username", None),
        employee_id=model.employee_id,
        first_name=model.first_name,
        last_name=model.last_name,
        display_name=model.display_name,
        email=model.email,
        phone=model.phone,
        avatar_url=model.avatar_url,
        department=model.department,
        job_title=model.job_title,
        language=model.language,
        timezone=model.timezone,
        is_email_verified=bool(model.is_email_verified),
        email_verified_at=model.email_verified_at,
        failed_login_attempts=int(model.failed_login_attempts),
        locked_until=model.locked_until,
        last_login_at=model.last_login_at,
        last_login_ip=model.last_login_ip,
        must_change_password=bool(getattr(model, "must_change_password", False)),
        password_changed_at=getattr(model, "password_changed_at", None),
        status=status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        role_name=role_name,
    )
