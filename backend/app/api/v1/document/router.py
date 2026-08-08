"""Document Management API router."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status

from app.api.deps import DbSession, DocumentServiceDep
from app.api.security import (
    RequireDocumentDelete,
    RequireDocumentRead,
    RequireDocumentReindex,
    RequireDocumentUpdate,
    RequireDocumentUpload,
)
from app.api.v1.document.schemas import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUpdateRequest,
    StorageUsageResponse,
)
from app.application.dto.document import (
    DocumentListQuery,
    UpdateDocumentInput,
    UploadDocumentInput,
)
from app.application.use_cases.document import (
    GetDocumentStatusUseCase,
    GetDocumentUseCase,
    ListDocumentsUseCase,
    ReindexDocumentUseCase,
    RestoreDocumentUseCase,
    SoftDeleteDocumentUseCase,
    StorageUsageUseCase,
    UpdateDocumentUseCase,
    UploadDocumentUseCase,
)
from app.core.pagination import Page
from app.core.responses.envelopes import success_envelope
from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus
from app.domain.exceptions.document import DocumentValidationError

router = APIRouter(prefix="/documents", tags=["Documents"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
}


def _to_response(document: Document) -> dict[str, Any]:
    return DocumentResponse.from_entity(document).model_dump(mode="json")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Upload document",
    description=(
        "Upload a knowledge document (multipart). Validates type/size, stores the "
        "binary via the configured object storage adapter, persists metadata, and "
        "sets processing status to QUEUED for a future AI pipeline."
    ),
    responses={**_AUTH_RESPONSES, 409: {"description": "Duplicate file hash"}},
)
async def upload_document(
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentUpload,
    file: Annotated[UploadFile, File(description="Document file")],
    document_name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    language: Annotated[str, Form()] = "en",
    tags: Annotated[str | None, Form(description="JSON array of tag strings")] = None,
    company_id: Annotated[
        int | None,
        Form(description="Required for Super Admin when acting for a company"),
    ] = None,
) -> dict[str, Any]:
    raw_tags: list[str] = []
    if tags:
        try:
            parsed = json.loads(tags)
        except json.JSONDecodeError as exc:
            raise DocumentValidationError("tags must be a JSON array of strings.") from exc
        if not isinstance(parsed, list):
            raise DocumentValidationError("tags must be a JSON array of strings.")
        raw_tags = [str(t).strip() for t in parsed if str(t).strip()]

    content = await file.read()
    document = await UploadDocumentUseCase(session, service).execute(
        UploadDocumentInput(
            company_id=company_id,
            document_name=document_name,
            description=description,
            language=language,
            tags=raw_tags,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            content=content,
        ),
        actor,
    )
    return success_envelope(_to_response(document), message="Document uploaded.")


@router.get(
    "",
    summary="List documents",
    description="Paginated, filterable, searchable document metadata for the tenant.",
    responses=_AUTH_RESPONSES,
)
async def list_documents(
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    status_filter: Annotated[
        DocumentStatus | None,
        Query(alias="status", description="Filter by processing_status"),
    ] = None,
    uploaded_by: Annotated[int | None, Query()] = None,
    company_id: Annotated[int | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query()] = "desc",
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    page_result: Page[Document] = await ListDocumentsUseCase(session, service).execute(
        DocumentListQuery(
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
            uploaded_by=uploaded_by,
            company_id=company_id,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=include_deleted,
        ),
        actor,
    )
    return success_envelope(
        {
            "items": [_to_response(d) for d in page_result.items],
            "meta": page_result.meta.model_dump(mode="json"),
        }
    )


@router.get(
    "/storage",
    summary="Storage usage",
    description="Document count and storage consumption versus company quotas.",
    responses=_AUTH_RESPONSES,
)
async def storage_usage(
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentRead,
    company_id: Annotated[int | None, Query()] = None,
) -> dict[str, Any]:
    usage = await StorageUsageUseCase(session, service).execute(company_id, actor)
    return success_envelope(
        StorageUsageResponse(
            company_id=usage.company_id,
            document_count=usage.document_count,
            used_bytes=usage.used_bytes,
            max_documents=usage.max_documents,
            max_storage_bytes=usage.max_storage_bytes,
            remaining_documents=usage.remaining_documents,
            remaining_bytes=usage.remaining_bytes,
        ).model_dump(mode="json")
    )


@router.get(
    "/{document_id}",
    summary="Get document",
    responses={**_AUTH_RESPONSES, 404: {"description": "Not found"}},
)
async def get_document(
    document_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentRead,
) -> dict[str, Any]:
    document = await GetDocumentUseCase(session, service).execute(document_id, actor)
    return success_envelope(_to_response(document))


@router.get(
    "/{document_id}/status",
    summary="Get processing status",
    responses={**_AUTH_RESPONSES, 404: {"description": "Not found"}},
)
async def get_document_status(
    document_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentRead,
) -> dict[str, Any]:
    document = await GetDocumentStatusUseCase(session, service).execute(document_id, actor)
    return success_envelope(
        DocumentStatusResponse(
            document_id=document.document_id,
            processing_status=document.processing_status,
            processing_started_at=document.processing_started_at,
            processing_completed_at=document.processing_completed_at,
            indexed_at=document.indexed_at,
            total_chunks=document.total_chunks,
            failure_reason=document.failure_reason,
            is_ready=document.is_ready,
            is_failed=document.is_failed,
        ).model_dump(mode="json")
    )


@router.put(
    "/{document_id}",
    summary="Update document metadata",
    responses=_AUTH_RESPONSES,
)
async def update_document(
    document_id: Annotated[int, Path(ge=1)],
    body: DocumentUpdateRequest,
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentUpdate,
) -> dict[str, Any]:
    document = await UpdateDocumentUseCase(session, service).execute(
        document_id,
        UpdateDocumentInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(document), message="Document updated.")


@router.patch(
    "/{document_id}",
    summary="Patch document metadata",
    responses=_AUTH_RESPONSES,
)
async def patch_document(
    document_id: Annotated[int, Path(ge=1)],
    body: DocumentUpdateRequest,
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentUpdate,
) -> dict[str, Any]:
    document = await UpdateDocumentUseCase(session, service).execute(
        document_id,
        UpdateDocumentInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(document), message="Document updated.")


@router.delete(
    "/{document_id}",
    summary="Soft-delete document",
    responses=_AUTH_RESPONSES,
)
async def delete_document(
    document_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentDelete,
) -> dict[str, Any]:
    document = await SoftDeleteDocumentUseCase(session, service).execute(document_id, actor)
    return success_envelope(_to_response(document), message="Document deleted.")


@router.post(
    "/{document_id}/restore",
    summary="Restore soft-deleted document",
    responses=_AUTH_RESPONSES,
)
async def restore_document(
    document_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentDelete,
) -> dict[str, Any]:
    document = await RestoreDocumentUseCase(session, service).execute(document_id, actor)
    return success_envelope(_to_response(document), message="Document restored.")


@router.post(
    "/{document_id}/reindex",
    summary="Queue document for reindexing",
    description=(
        "Marks the document as QUEUED for a future RAG/indexing worker. "
        "Does not extract text, embed, or write to a vector store."
    ),
    responses=_AUTH_RESPONSES,
)
async def reindex_document(
    document_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: DocumentServiceDep,
    actor: RequireDocumentReindex,
) -> dict[str, Any]:
    document = await ReindexDocumentUseCase(session, service).execute(document_id, actor)
    return success_envelope(_to_response(document), message="Document queued for reindex.")
