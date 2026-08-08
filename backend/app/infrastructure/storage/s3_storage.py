"""S3 / R2 object storage adapter — placeholder until cloud storage is wired."""

from __future__ import annotations

from app.domain.enums.document_status import StorageProvider


class S3ObjectStorage:
    """Reserved for AWS S3 / R2. Local development uses LocalObjectStorage."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        _ = args, kwargs
        raise NotImplementedError(
            "S3/R2 storage is not configured for this environment. "
            "Set STORAGE_PROVIDER=local for development."
        )

    @property
    def provider_name(self) -> str:
        return StorageProvider.AWS_S3.value

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        raise NotImplementedError

    async def get(self, key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError
