"""Root API router aggregator."""

from fastapi import APIRouter

from app.api.v1.health.router import router as health_router
from app.api.v1.router import api_v1_router

# Health probes live at the application root (/health, /ready).
health_api_router = APIRouter()
health_api_router.include_router(health_router)

# Versioned business routes are mounted with a prefix in create_app().
__all__ = ["api_v1_router", "health_api_router"]
