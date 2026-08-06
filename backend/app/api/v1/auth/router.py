"""Authentication API router.

OpenAPI tag: **Authentication**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | public | Issue access + refresh JWT pair |
| POST | `/auth/refresh` | public | Rotate refresh token |
| POST | `/auth/logout` | optional | Revoke refresh token(s) |
| GET | `/auth/me` | Bearer | Current authenticated principal |
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status

from app.api.deps import AuthServiceDep, CurrentUserDep, DbSession, OptionalActorDep
from app.api.v1.auth.schemas import (
    AuthUserResponse,
    LoginRequest,
    LoginResponseData,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.application.services.auth.auth_service import AuthSession
from app.application.use_cases.auth.auth_use_cases import (
    GetCurrentUserUseCase,
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
)
from app.core.responses.envelopes import success_envelope
from app.domain.entities.user import AuthUser
from app.domain.exceptions.auth import TokenInvalidError

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    return ip, request.headers.get("User-Agent")


def _user_response(user: AuthUser) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user.user_id,
        company_id=user.company_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        role_name=user.role_name,
        permissions=sorted(user.permissions),
        is_super_admin=user.is_super_admin,
    )


def _session_payload(session: AuthSession) -> dict[str, Any]:
    return LoginResponseData(
        tokens=TokenResponse(
            access_token=session.tokens.access_token,
            refresh_token=session.tokens.refresh_token,
            token_type=session.tokens.token_type,
            expires_in=session.tokens.expires_in,
        ),
        user=_user_response(session.user),
    ).model_dump(mode="json")


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description=(
        "Authenticate with email/password (Argon2 verified). "
        "Returns a short-lived JWT access token and an opaque refresh token. "
        "Accounts may lock after repeated failures."
    ),
    responses={
        200: {"description": "Login successful; tokens and user profile returned."},
        401: {"description": "Invalid credentials (`INVALID_CREDENTIALS`)."},
        403: {"description": "Account locked or inactive."},
    },
)
async def login(
    body: LoginRequest,
    request: Request,
    session: DbSession,
    service: AuthServiceDep,
) -> dict[str, Any]:
    """Authenticate a user and return JWT access + refresh tokens."""
    ip, user_agent = _client_meta(request)
    result = await LoginUseCase(session, service).execute(
        email=str(body.email),
        password=body.password,
        ip_address=ip,
        user_agent=user_agent,
    )
    return success_envelope(_session_payload(result), message="Login successful.")


@router.post(
    "/refresh",
    summary="Rotate refresh token and issue a new access token",
    description=(
        "Validates the refresh token hash, revokes the previous token, "
        "and issues a new access + refresh pair (rotation)."
    ),
    responses={
        200: {"description": "Tokens rotated."},
        401: {"description": "Refresh token invalid, expired, or already used."},
    },
)
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: DbSession,
    service: AuthServiceDep,
) -> dict[str, Any]:
    ip, user_agent = _client_meta(request)
    result = await RefreshTokenUseCase(session, service).execute(
        refresh_token=body.refresh_token,
        ip_address=ip,
        user_agent=user_agent,
    )
    return success_envelope(_session_payload(result), message="Token refreshed.")


@router.post(
    "/logout",
    summary="Revoke refresh token(s)",
    description=(
        "Revokes the supplied refresh token. Pass `revoke_all=true` with a valid "
        "Bearer access token to revoke every refresh token for the user."
    ),
    responses={200: {"description": "Logged out."}},
)
async def logout(
    body: LogoutRequest,
    session: DbSession,
    service: AuthServiceDep,
    actor: OptionalActorDep,
) -> dict[str, Any]:
    """Logout using refresh token and/or authenticated access token."""
    await LogoutUseCase(session, service).execute(
        refresh_token=body.refresh_token,
        user_id=actor.user_id,
        revoke_all=body.revoke_all,
    )
    return success_envelope(message="Logged out.")


@router.get(
    "/me",
    summary="Current authenticated user",
    description="Requires `Authorization: Bearer <access_token>`.",
    responses={
        200: {"description": "Authenticated user profile and permissions."},
        401: {"description": "Missing or invalid access token."},
    },
)
async def me(
    service: AuthServiceDep,
    actor: CurrentUserDep,
) -> dict[str, Any]:
    """Return the authenticated principal (requires Bearer access token)."""
    if actor.user_id is None:
        raise TokenInvalidError("Authentication required.")
    user = await GetCurrentUserUseCase(service).execute(actor.user_id)
    return success_envelope(_user_response(user).model_dump(mode="json"))
