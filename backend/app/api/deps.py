"""FastAPI dependency injection providers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.services.auth.auth_service import AuthService
from app.application.services.company.company_service import CompanyService
from app.application.services.role.role_service import RoleService
from app.application.services.user.user_service import UserService
from app.core.config import Settings, get_settings
from app.core.security.http import bearer_scheme
from app.domain.enums.company_status import CompanyStatus
from app.domain.exceptions.auth import InsufficientPermissionError, TokenInvalidError
from app.domain.exceptions.company import CompanyInactiveError
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.infrastructure.audit.logging_audit_logger import LoggingAuditLogger
from app.infrastructure.database.repositories.auth_user_repository import (
    SQLAlchemyAuthUserRepository,
)
from app.infrastructure.database.repositories.company_repository import (
    SQLAlchemyCompanyRepository,
)
from app.infrastructure.database.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.database.session import get_db

_ACTIVE_COMPANY_STATUSES = frozenset({CompanyStatus.ACTIVE, CompanyStatus.TRIAL})


def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_audit_logger() -> AuditLogger:
    return LoggingAuditLogger()


def get_company_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> CompanyService:
    return CompanyService(
        repository=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


def get_user_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> UserService:
    return UserService(
        users=SQLAlchemyUserRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        refresh_tokens=SQLAlchemyRefreshTokenRepository(session),
        audit_logger=audit_logger,
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_role_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> RoleService:
    return RoleService(
        roles=SQLAlchemyRoleRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]


def get_auth_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> AuthService:
    return AuthService(
        users=SQLAlchemyAuthUserRepository(session),
        refresh_tokens=SQLAlchemyRefreshTokenRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def _assert_company_active_for_actor(
    session: AsyncSession,
    actor: RequestActor,
) -> None:
    """Block protected APIs when the caller's tenant is not ACTIVE/TRIAL."""
    if actor.is_super_admin or actor.company_id is None:
        return
    company = await SQLAlchemyCompanyRepository(session).get_by_id(actor.company_id)
    if company is None or company.status not in _ACTIVE_COMPANY_STATUSES:
        raise CompanyInactiveError()


async def get_optional_actor(
    request: Request,
    settings: SettingsDep,
    service: AuthServiceDep,
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_company_id: Annotated[int | None, Header(alias="X-Company-Id")] = None,
    x_super_admin: Annotated[str | None, Header(alias="X-Super-Admin")] = None,
) -> RequestActor:
    """Resolve caller from JWT when present; optional header bypass in tests."""
    auth_error = getattr(request.state, "auth_error", None)
    claims = getattr(request.state, "token_claims", None)

    if claims is not None:
        user_id = int(claims["sub"])
        user = await service.get_authenticated_user(user_id)
        actor = service.to_actor(user)
        request.state.actor = actor
        return actor

    if auth_error is not None:
        # Bearer present but invalid — preserve error for required-auth deps.
        request.state.actor = RequestActor()
        return RequestActor()

    if settings.auth_header_bypass:
        is_super_admin = False
        if x_super_admin is not None:
            is_super_admin = x_super_admin.strip().lower() in {"1", "true", "yes"}
        actor = RequestActor(
            user_id=x_user_id,
            company_id=x_company_id,
            is_super_admin=is_super_admin,
            role_name="SUPER_ADMIN" if is_super_admin else None,
            permissions=frozenset() if not is_super_admin else frozenset(),
        )
        request.state.actor = actor
        return actor

    actor = RequestActor()
    request.state.actor = actor
    return actor


OptionalActorDep = Annotated[RequestActor, Depends(get_optional_actor)]


async def get_current_actor(
    request: Request,
    session: DbSession,
    settings: SettingsDep,
    actor: OptionalActorDep,
    _credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ] = None,
) -> RequestActor:
    """Require a valid authenticated user (JWT). Alias: CurrentUser."""
    auth_error = getattr(request.state, "auth_error", None)
    if auth_error is not None:
        raise auth_error

    authenticated = actor.user_id is not None or (
        settings.auth_header_bypass and actor.is_super_admin
    )
    if not authenticated:
        raise TokenInvalidError("Authentication required.")

    await _assert_company_active_for_actor(session, actor)
    return actor


CurrentActorDep = Annotated[RequestActor, Depends(get_current_actor)]
# PRD / acceptance wording.
CurrentUserDep = CurrentActorDep


# Optional actor for public endpoints (registration, login helpers).
async def get_request_actor(actor: OptionalActorDep) -> RequestActor:
    return actor


RequestActorDep = Annotated[RequestActor, Depends(get_request_actor)]


def require_permissions(*permissions: str) -> Callable[..., RequestActor]:
    """Permission dependency factory (RBAC). Requires authenticated CurrentUser."""

    async def _dependency(actor: CurrentActorDep) -> RequestActor:
        if not actor.has_all_permissions(*permissions):
            raise InsufficientPermissionError(
                f"Missing permission(s): {', '.join(permissions)}",
            )
        return actor

    return _dependency


require_permissions_dep = require_permissions
