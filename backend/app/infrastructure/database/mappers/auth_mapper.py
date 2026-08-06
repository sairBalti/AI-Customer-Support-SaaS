"""Map auth ORM models to domain entities."""

from __future__ import annotations

from app.domain.entities.refresh_token import RefreshToken
from app.domain.entities.user import AuthUser
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.auth import RefreshTokenModel, UserModel


def user_to_auth_entity(
    model: UserModel,
    *,
    role_name: str | None = None,
    permissions: frozenset[str] | None = None,
) -> AuthUser:
    status = model.status if isinstance(model.status, UserStatus) else UserStatus(str(model.status))
    return AuthUser(
        user_id=int(model.user_id),
        company_id=int(model.company_id),
        role_id=int(model.role_id),
        email=model.email,
        password_hash=model.password_hash,
        first_name=model.first_name,
        last_name=model.last_name,
        display_name=model.display_name,
        status=status,
        is_email_verified=bool(model.is_email_verified),
        failed_login_attempts=int(model.failed_login_attempts),
        locked_until=model.locked_until,
        last_login_at=model.last_login_at,
        last_login_ip=model.last_login_ip,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        role_name=role_name,
        permissions=permissions or frozenset(),
    )


def refresh_token_to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        token_id=int(model.token_id),
        user_id=int(model.user_id),
        company_id=int(model.company_id),
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        created_at=model.created_at,
        revoked_at=model.revoked_at,
        replaced_by_token_id=(
            int(model.replaced_by_token_id) if model.replaced_by_token_id is not None else None
        ),
        user_agent=model.user_agent,
        ip_address=model.ip_address,
    )
