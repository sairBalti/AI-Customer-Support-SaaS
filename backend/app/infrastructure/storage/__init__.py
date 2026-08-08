"""Object storage package."""

from app.infrastructure.storage.factory import build_object_storage, get_object_storage
from app.infrastructure.storage.local_storage import LocalObjectStorage

__all__ = [
    "LocalObjectStorage",
    "build_object_storage",
    "get_object_storage",
]
