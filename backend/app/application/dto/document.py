"""Document application DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums.document_status import DocumentStatus


@dataclass(slots=True)
class UploadDocumentInput:
    company_id: int | None
    document_name: str | None
    description: str | None
    language: str
    tags: list[str]
    filename: str
    content_type: str | None
    content: bytes


@dataclass(slots=True)
class UpdateDocumentInput:
    values: dict[str, Any]


@dataclass(slots=True)
class DocumentListQuery:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    status: DocumentStatus | None = None
    uploaded_by: int | None = None
    company_id: int | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    include_deleted: bool = False


@dataclass(slots=True)
class StorageUsageResult:
    company_id: int
    document_count: int
    used_bytes: int
    max_documents: int
    max_storage_bytes: int
    remaining_documents: int
    remaining_bytes: int
