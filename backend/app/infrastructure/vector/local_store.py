"""File-backed local vector store (dev substitute under CHROMA_PERSIST_DIR)."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from typing import Any

from app.domain.interfaces.services.vector_store import VectorRecord, VectorSearchHit


class LocalPersistentVectorStore:
    """Persist vectors as JSON under ``root_dir`` with mandatory company filtering."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir).resolve() / "local_vectors"
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "index.json"
        if not self._index_path.exists():
            self._write_index({})

    @property
    def provider_name(self) -> str:
        return "local"

    def _read_index(self) -> dict[str, Any]:
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            return {}

    def _write_index(self, data: dict[str, Any]) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(self._index_path)

    async def upsert(self, records: list[VectorRecord]) -> None:
        def _upsert() -> None:
            index = self._read_index()
            for record in records:
                meta = dict(record.metadata)
                if "company_id" not in meta:
                    raise ValueError("VectorRecord.metadata must include company_id")
                index[record.id] = {
                    "id": record.id,
                    "embedding": record.embedding,
                    "content": record.content,
                    "metadata": meta,
                }
            self._write_index(index)

        await asyncio.to_thread(_upsert)

    async def delete(self, ids: list[str]) -> None:
        def _delete() -> None:
            index = self._read_index()
            changed = False
            for item_id in ids:
                if item_id in index:
                    del index[item_id]
                    changed = True
            if changed:
                self._write_index(index)

        await asyncio.to_thread(_delete)

    async def delete_by_document(self, *, company_id: int, document_id: int) -> int:
        def _delete() -> int:
            index = self._read_index()
            remove_ids = [
                key
                for key, row in index.items()
                if int(row.get("metadata", {}).get("company_id", -1)) == int(company_id)
                and int(row.get("metadata", {}).get("document_id", -1)) == int(document_id)
            ]
            for key in remove_ids:
                del index[key]
            if remove_ids:
                self._write_index(index)
            return len(remove_ids)

        return await asyncio.to_thread(_delete)

    async def similarity_search(
        self,
        *,
        company_id: int,
        query_embedding: list[float],
        top_k: int,
        document_id: int | None = None,
    ) -> list[VectorSearchHit]:
        def _search() -> list[VectorSearchHit]:
            index = self._read_index()
            hits: list[VectorSearchHit] = []
            for row in index.values():
                meta = row.get("metadata") or {}
                if int(meta.get("company_id", -1)) != int(company_id):
                    continue
                if document_id is not None and int(meta.get("document_id", -1)) != int(document_id):
                    continue
                score = _cosine(query_embedding, row.get("embedding") or [])
                hits.append(
                    VectorSearchHit(
                        id=str(row["id"]),
                        content=str(row.get("content") or ""),
                        score=score,
                        metadata=dict(meta),
                    )
                )
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[: max(top_k, 0)]

        return await asyncio.to_thread(_search)

    async def health(self) -> bool:
        return await asyncio.to_thread(lambda: self._root.exists())


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
