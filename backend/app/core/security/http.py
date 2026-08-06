"""OpenAPI / FastAPI security schemes for JWT Bearer auth."""

from __future__ import annotations

from fastapi.security import HTTPBearer

# `auto_error=False` lets CurrentActorDep raise domain TokenInvalidError (401 envelope)
# instead of FastAPI's default 403 when the header is missing.
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=(
        "JWT access token. Obtain via `POST /api/v1/auth/login`, "
        "then click Authorize and paste: `<access_token>`."
    ),
)

BEARER_SECURITY = [{"BearerAuth": []}]
