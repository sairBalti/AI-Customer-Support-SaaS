"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.middleware.auth import AuthenticationMiddleware
from app.api.middleware.rbac import RBACMiddleware
from app.api.router import api_v1_router, health_api_router
from app.core.config import get_settings
from app.core.exceptions.handlers import register_exception_handlers
from app.core.logging.setup import configure_logging
from app.infrastructure.database.session import dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan.

    Startup does not connect to MySQL so the process can boot when the
    database is unavailable. Shutdown disposes the engine if it was created.
    """
    logger.info("Application starting (database connect deferred until first use)")
    yield
    await dispose_engine()
    logger.info("Application shutdown complete")


def _custom_openapi(application: FastAPI) -> dict[str, Any]:
    if application.openapi_schema:
        return application.openapi_schema
    schema = get_openapi(
        title=application.title,
        version=getattr(application, "version", "1.0.0") or "1.0.0",
        description=(
            "AI Customer Support Agent API.\n\n"
            "## Authentication\n"
            "1. Call `POST /api/v1/auth/login` to obtain an access token.\n"
            "2. Click **Authorize** and paste the access token "
            "(Swagger adds the `Bearer` prefix).\n"
            "3. Protected endpoints require a valid JWT; admin endpoints also "
            "require RBAC permissions (`companies.manage`, etc.).\n\n"
            "Public endpoints: company registration, login, refresh."
        ),
        routes=application.routes,
    )
    components = schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})
    schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT access token from `/api/v1/auth/login`.",
    }
    application.openapi_schema = schema
    return application.openapi_schema


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(debug=settings.debug)

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        swagger_ui_init_oauth={},
    )

    # Last added runs first on the request path.
    application.add_middleware(RBACMiddleware)
    application.add_middleware(AuthenticationMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(health_api_router)
    application.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    application.openapi = lambda: _custom_openapi(application)  # type: ignore[method-assign]

    return application


app = create_app()
