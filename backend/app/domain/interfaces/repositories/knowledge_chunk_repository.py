"""Knowledge chunk repository port."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities.knowledge_chunk import KnowledgeChunk


class KnowledgeChunkRepository(Protocol):
    async def bulk_create(self, rows: list[dict[str, Any]]) -> list[KnowledgeChunk]: ...

    async def list_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> list[KnowledgeChunk]: ...

    async def get_by_uuid(self, chunk_uuid: str) -> KnowledgeChunk | None: ...

    async def delete_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> int: ...

    async def count_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> int: ...
