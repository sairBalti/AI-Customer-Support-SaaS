"""Chroma package adapter placeholder — local file store is used by default."""

from __future__ import annotations

from app.infrastructure.vector.local_store import LocalPersistentVectorStore

# Re-export local store under chroma naming for VECTOR_STORE_PROVIDER=chroma.
ChromaVectorStore = LocalPersistentVectorStore
