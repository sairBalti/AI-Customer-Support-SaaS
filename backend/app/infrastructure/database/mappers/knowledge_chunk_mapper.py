"""Map KnowledgeChunk ORM rows to domain entities."""

from __future__ import annotations

from app.domain.entities.knowledge_chunk import KnowledgeChunk
from app.infrastructure.database.models.knowledge_chunk import KnowledgeChunkModel


def knowledge_chunk_to_entity(model: KnowledgeChunkModel) -> KnowledgeChunk:
    metadata = model.chunk_metadata if isinstance(model.chunk_metadata, dict) else {}
    return KnowledgeChunk(
        chunk_id=int(model.chunk_id),
        company_id=int(model.company_id),
        document_id=int(model.document_id),
        chunk_number=int(model.chunk_number),
        chunk_uuid=model.chunk_uuid,
        embedding_id=model.embedding_id,
        chunk_text=model.chunk_text,
        token_count=int(model.token_count),
        character_count=int(model.character_count),
        embedding_provider=model.embedding_provider,
        embedding_model=model.embedding_model,
        embedding_dimension=int(model.embedding_dimension),
        language=model.language,
        version=int(model.version),
        retrieval_count=int(model.retrieval_count),
        created_at=model.created_at,
        updated_at=model.updated_at,
        page_number=model.page_number,
        section_title=model.section_title,
        overlap_previous=bool(model.overlap_previous),
        overlap_next=bool(model.overlap_next),
        last_retrieved_at=model.last_retrieved_at,
        metadata={str(k): v for k, v in metadata.items()},
    )
