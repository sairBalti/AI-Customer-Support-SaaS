"""Factories for knowledge/RAG infrastructure adapters."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.domain.interfaces.services.embedding_service import EmbeddingProvider
from app.domain.interfaces.services.text_chunker import TextChunker
from app.domain.interfaces.services.text_extractor import DocumentProcessor
from app.domain.interfaces.services.vector_store import VectorStore
from app.infrastructure.knowledge.chunker import RecursiveCharacterChunker
from app.infrastructure.knowledge.document_processor import DefaultDocumentProcessor
from app.infrastructure.knowledge.embeddings.hashing import HashingEmbeddingProvider
from app.infrastructure.vector.local_store import LocalPersistentVectorStore


def build_document_processor(_settings: Settings | None = None) -> DocumentProcessor:
    return DefaultDocumentProcessor()


def build_text_chunker(settings: Settings | None = None) -> TextChunker:
    cfg = settings or get_settings()
    return RecursiveCharacterChunker(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    cfg = settings or get_settings()
    provider = (cfg.embedding_provider or "hashing").strip().lower()
    if provider in {"hashing", "local", "dev"}:
        return HashingEmbeddingProvider(dimension=cfg.embedding_dimension)
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={cfg.embedding_provider!r}. "
        "Use 'hashing' for local development (no paid API keys)."
    )


def build_vector_store(settings: Settings | None = None) -> VectorStore:
    cfg = settings or get_settings()
    provider = (cfg.vector_store_provider or "chroma").strip().lower()
    if provider in {"chroma", "local", "memory", "file"}:
        return LocalPersistentVectorStore(cfg.chroma_persist_dir)
    if provider == "pinecone":
        raise ValueError(
            "Pinecone requires a dedicated adapter and paid credentials. "
            "Use VECTOR_STORE_PROVIDER=chroma for local development."
        )
    raise ValueError(f"Unsupported VECTOR_STORE_PROVIDER={cfg.vector_store_provider!r}.")


@lru_cache
def get_document_processor() -> DocumentProcessor:
    return build_document_processor()


@lru_cache
def get_text_chunker() -> TextChunker:
    return build_text_chunker()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider()


@lru_cache
def get_vector_store() -> VectorStore:
    return build_vector_store()
