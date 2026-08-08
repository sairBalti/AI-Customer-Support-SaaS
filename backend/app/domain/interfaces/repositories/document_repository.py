"""Document repository port."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus


class DocumentRepository(Protocol):
    async def create(self, data: dict[str, Any]) -> Document: ...

    async def get_by_id(
        self,
        document_id: int,
        *,
        include_deleted: bool = False,
    ) -> Document | None: ...

    async def get_by_hash(
        self,
        company_id: int,
        file_hash: str,
        *,
        include_deleted: bool = False,
    ) -> Document | None: ...

    async def update(
        self,
        document_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Document | None: ...

    async def soft_delete(self, document_id: int, *, at: datetime) -> Document | None: ...

    async def restore(self, document_id: int) -> Document | None: ...

    async def search(
        self,
        *,
        company_id: int | None,
        search: str | None,
        status: DocumentStatus | None,
        uploaded_by: int | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[Document], int]: ...

    async def count_by_company(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int: ...

    async def sum_storage_bytes(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int: ...
