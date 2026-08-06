"""Smoke test: Swagger/OpenAPI exposes BearerAuth Authorize scheme."""

from app.main import create_app


def test_openapi_defines_bearer_auth_scheme() -> None:
    app = create_app()
    schema = app.openapi()
    schemes = schema["components"]["securitySchemes"]
    assert "BearerAuth" in schemes
    assert schemes["BearerAuth"]["type"] == "http"
    assert schemes["BearerAuth"]["scheme"] == "bearer"

    paths = schema["paths"]
    # Registration stays public (no lock icon).
    assert not paths["/api/v1/companies"]["post"].get("security")
    assert not paths["/api/v1/auth/login"]["post"].get("security")
    assert not paths["/api/v1/auth/refresh"]["post"].get("security")

    # Protected company list is marked for Authorize / Bearer.
    list_security = paths["/api/v1/companies"]["get"].get("security") or []
    assert {"BearerAuth": []} in list_security
