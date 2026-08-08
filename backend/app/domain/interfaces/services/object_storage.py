"""Object storage port (local filesystem / S3 / compatible backends)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """Binary object storage — domain must not depend on FS or cloud SDKs."""

    @property
    def provider_name(self) -> str:
        """StorageProvider enum value as string (e.g. LOCAL, AWS_S3)."""
        ...

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        """Store bytes at ``key``. Returns the canonical storage key/path."""
        ...

    async def get(self, key: str) -> bytes:
        """Read object bytes."""
        ...

    async def delete(self, key: str) -> None:
        """Delete object if it exists (idempotent)."""
        ...

    async def exists(self, key: str) -> bool:
        """Return True when the object is present."""
        ...
