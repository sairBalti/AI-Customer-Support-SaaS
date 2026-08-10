"""Grounded prompting helpers for the support agent."""

from __future__ import annotations

from app.domain.entities.knowledge_chunk import RetrievedChunk

NO_CONTEXT_ANSWER = (
    "I do not have enough information in the company knowledge base "
    "to answer that question. Please rephrase, or contact a human support agent."
)

GROUNDED_SYSTEM_PROMPT = """You are a customer support assistant for a single company.
Answer ONLY using the knowledge context provided below.
Rules:
- Do not invent facts that are not supported by the knowledge context.
- If the knowledge context is missing or insufficient, say clearly that the
  company knowledge base does not contain enough information.
- Do not use general world knowledge as a substitute for company documents.
- Distinguish document-backed statements from any necessary clarifying questions.
- Keep answers concise and professional.
"""


def format_retrieval_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.source_filename or f"document_{chunk.document_id}"
        page = f", page {chunk.page_number}" if chunk.page_number is not None else ""
        blocks.append(
            f"[{index}] source={source} document_id={chunk.document_id} "
            f"chunk_id={chunk.chunk_id}{page} score={chunk.score:.4f}\n"
            f"{chunk.content.strip()}"
        )
    return "\n\n".join(blocks)


def citations_from_chunks(
    chunks: list[RetrievedChunk],
    *,
    document_names: dict[int, str] | None = None,
) -> list[dict[str, object]]:
    names = document_names or {}
    items: list[dict[str, object]] = []
    for chunk in chunks:
        items.append(
            {
                "document_id": chunk.document_id,
                "document_name": names.get(chunk.document_id)
                or chunk.source_filename
                or f"document_{chunk.document_id}",
                "chunk_id": chunk.chunk_id,
                "chunk_uuid": chunk.chunk_uuid,
                "page": chunk.page_number,
                "score": round(float(chunk.score), 6),
            }
        )
    return items
