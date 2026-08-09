"""Knowledge Base / RAG API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.deps import DbSession, KnowledgeServiceDep
from app.api.security import RequireKnowledgeSearch
from app.api.v1.knowledge.schemas import KnowledgeSearchHitResponse, KnowledgeSearchRequest
from app.application.dto.knowledge import KnowledgeSearchInput
from app.application.use_cases.knowledge import SearchKnowledgeUseCase
from app.core.responses.envelopes import success_envelope

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
}


@router.post(
    "/search",
    summary="Search company knowledge",
    description=(
        "Retrieve ranked document chunks for a query. Always scoped to the caller's "
        "company (Super Admin may pass company_id). Does not invoke an LLM."
    ),
    responses=_AUTH_RESPONSES,
)
async def search_knowledge(
    body: KnowledgeSearchRequest,
    session: DbSession,
    service: KnowledgeServiceDep,
    actor: RequireKnowledgeSearch,
) -> dict[str, Any]:
    hits = await SearchKnowledgeUseCase(session, service).execute(
        KnowledgeSearchInput(
            query=body.query,
            top_k=body.top_k,
            document_id=body.document_id,
            company_id=body.company_id,
        ),
        actor,
    )
    return success_envelope(
        {
            "items": [
                KnowledgeSearchHitResponse(
                    document_id=h.document_id,
                    chunk_id=h.chunk_id,
                    chunk_uuid=h.chunk_uuid,
                    content=h.content,
                    score=h.score,
                    chunk_index=h.chunk_index,
                    source_filename=h.source_filename,
                    page_number=h.page_number,
                    metadata=h.metadata,
                ).model_dump(mode="json")
                for h in hits
            ]
        }
    )
