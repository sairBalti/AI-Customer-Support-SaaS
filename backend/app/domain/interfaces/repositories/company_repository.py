"""Company repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan


class CompanyRepository(ABC):
    """Persistence port for companies. No business rules here."""

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Company:
        """Persist a new company and return the domain entity."""

    @abstractmethod
    async def get_by_id(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        """Fetch a company by primary key."""

    @abstractmethod
    async def get_by_slug(
        self,
        company_slug: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        """Fetch a company by unique slug."""

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        """Fetch a company by unique email."""

    @abstractmethod
    async def get_by_name(
        self,
        company_name: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        """Fetch a company by unique name."""

    @abstractmethod
    async def update(
        self,
        company_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        """Apply partial updates and return the updated entity."""

    @abstractmethod
    async def update_subscription(
        self,
        company_id: int,
        *,
        subscription_plan: SubscriptionPlan,
        max_users: int,
        max_documents: int,
        max_storage_mb: int,
        monthly_ai_tokens: int,
        subscription_expires_at: Any | None,
    ) -> Company | None:
        """Update subscription fields for a company."""

    @abstractmethod
    async def update_usage(self, company_id: int, token_usage: int) -> Company | None:
        """Update AI token usage counters."""

    @abstractmethod
    async def soft_delete(self, company_id: int) -> Company | None:
        """Soft-delete a company (set deleted_at; never hard-delete)."""

    @abstractmethod
    async def archive(self, company_id: int) -> Company | None:
        """Archive a company (status ARCHIVED + soft delete marker)."""

    @abstractmethod
    async def list_active(self) -> list[Company]:
        """List non-deleted companies with ACTIVE status."""

    @abstractmethod
    async def search(
        self,
        *,
        search: str | None = None,
        status: CompanyStatus | None = None,
        subscription_plan: SubscriptionPlan | None = None,
        company_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[Company], int]:
        """Search/filter/sort companies with pagination. Returns (items, total)."""
