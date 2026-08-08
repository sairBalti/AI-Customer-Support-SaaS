"""Local filesystem object storage adapter."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.domain.enums.document_status import StorageProvider


class LocalObjectStorage:
    """Stores objects under ``root_dir`` keyed by relative paths."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return StorageProvider.LOCAL.value

    def _resolve(self, key: str) -> Path:
        cleaned = key.replace("\\", "/").lstrip("/")
        path = (self._root / cleaned).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("Invalid storage key.") from exc
        return path

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        _ = content_type
        path = self._resolve(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return key.replace("\\", "/").lstrip("/")

    async def get(self, key: str) -> bytes:
        path = self._resolve(key)

        def _read() -> bytes:
            return path.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)

        def _unlink() -> None:
            if path.is_file():
                path.unlink()

        await asyncio.to_thread(_unlink)

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return await asyncio.to_thread(path.is_file)
