"""Map Document ORM rows to domain entities."""

from __future__ import annotations

from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.infrastructure.database.models.document import DocumentModel


def document_to_entity(model: DocumentModel) -> Document:
    tags = model.tags if isinstance(model.tags, list) else []
    metadata = model.doc_metadata if isinstance(model.doc_metadata, dict) else {}
    return Document(
        document_id=int(model.document_id),
        company_id=int(model.company_id),
        uploaded_by=int(model.uploaded_by),
        document_name=model.document_name,
        original_filename=model.original_filename,
        storage_path=model.storage_path,
        storage_provider=StorageProvider(model.storage_provider),
        mime_type=model.mime_type,
        file_extension=model.file_extension,
        file_size_bytes=int(model.file_size_bytes),
        file_hash=model.file_hash,
        processing_status=DocumentStatus(model.processing_status),
        language=model.language,
        version=int(model.version),
        total_chunks=int(model.total_chunks),
        created_at=model.created_at,
        updated_at=model.updated_at,
        page_count=model.page_count,
        embedding_provider=model.embedding_provider,
        embedding_model=model.embedding_model,
        processing_started_at=model.processing_started_at,
        processing_completed_at=model.processing_completed_at,
        indexed_at=model.indexed_at,
        last_accessed_at=model.last_accessed_at,
        description=model.description,
        tags=[str(t) for t in tags],
        metadata={str(k): v for k, v in metadata.items()},
        deleted_at=model.deleted_at,
        failure_reason=model.failure_reason,
    )
