"""Shared audit metadata sanitization (never log/store secrets)."""

from __future__ import annotations

from typing import Any

_SENSITIVE_METADATA_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "token",
        "api_key",
        "secret",
        "secret_key",
        "gemini_api_key",
        "openai_api_key",
        "authorization",
    }
)

# Safe business correlation ids that contain "token" as a substring.
_SAFE_CORRELATION_KEYS = frozenset({"token_id"})


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = str(key).lower()
        if lowered in _SAFE_CORRELATION_KEYS:
            cleaned[key] = value
            continue
        if lowered in _SENSITIVE_METADATA_KEYS or any(
            s in lowered for s in ("password", "token", "secret", "api_key")
        ):
            continue
        cleaned[key] = value
    return cleaned
