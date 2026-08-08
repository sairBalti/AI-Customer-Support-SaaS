"""Object storage factory — selects adapter from application settings."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.domain.enums.document_status import StorageProvider
from app.domain.interfaces.services.object_storage import ObjectStorage
from app.infrastructure.storage.local_storage import LocalObjectStorage


def build_object_storage(settings: Settings | None = None) -> ObjectStorage:
    """Create the configured object storage adapter."""
    cfg = settings or get_settings()
    provider = (cfg.storage_provider or "local").strip().lower()
    if provider in {"local", StorageProvider.LOCAL.value.lower()}:
        return LocalObjectStorage(cfg.local_storage_path)
    raise ValueError(
        f"Unsupported STORAGE_PROVIDER={cfg.storage_provider!r}. "
        "Use 'local' for development (S3/R2 adapters are reserved for later)."
    )


@lru_cache
def get_object_storage() -> ObjectStorage:
    return build_object_storage()
