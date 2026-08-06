"""Pagination helpers."""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Shared list pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta

    @classmethod
    def of(cls, items: list[T], *, page: int, page_size: int, total_items: int) -> Page[T]:
        total_pages = math.ceil(total_items / page_size) if page_size else 0
        return cls(
            items=items,
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
            ),
        )
