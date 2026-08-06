"""Health and readiness probes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infrastructure.database.session import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — process is up (independent of MySQL)."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — reports MySQL connectivity without crashing startup."""
    database_ok = await check_database_connection()
    payload = {
        "status": "ready" if database_ok else "unavailable",
        "checks": {
            "database": "ok" if database_ok else "unavailable",
        },
    }
    status_code = 200 if database_ok else 503
    return JSONResponse(status_code=status_code, content=payload)
