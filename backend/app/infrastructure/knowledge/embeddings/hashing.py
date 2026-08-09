"""Deterministic hashing embedding provider (no paid API keys)."""

from __future__ import annotations

import hashlib
import math


class HashingEmbeddingProvider:
    """Local/dev embedding provider using SHA-256 expanded into a fixed vector."""

    def __init__(self, *, dimension: int = 64, model_name: str = "hashing-v1") -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self._dimension = dimension
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "hashing"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self._dimension:
            for byte in seed:
                # Map byte to [-1, 1]
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self._dimension:
                    break
            seed = hashlib.sha256(seed).digest()
        # L2 normalize for cosine similarity stability
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
