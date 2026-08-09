"""Knowledge API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: int | None = Field(default=None, ge=1)
    company_id: int | None = Field(default=None, ge=1)


class KnowledgeSearchHitResponse(BaseModel):
    document_id: int
    chunk_id: int | None
    chunk_uuid: str
    content: str
    score: float
    chunk_index: int
    source_filename: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
