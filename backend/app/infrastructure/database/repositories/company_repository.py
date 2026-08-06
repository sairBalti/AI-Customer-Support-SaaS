"""Company repository adapter (SQLAlchemy async)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.company.company_rules import SORTABLE_FIELDS, escape_like
from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.company import CompanyConflictError, CompanyValidationError
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.infrastructure.database.mappers.company_mapper import company_to_entity
from app.infrastructure.database.models.company import CompanyModel

_SORTABLE_COLUMNS: dict[str, Any] = {
    "created_at": CompanyModel.created_at,
    "updated_at": CompanyModel.updated_at,
    "company_name": CompanyModel.company_name,
    "status": CompanyModel.status,
    "subscription_plan": CompanyModel.subscription_plan,
    "last_activity_at": CompanyModel.last_activity_at,
    "subscription_expires_at": CompanyModel.subscription_expires_at,
}


class SQLAlchemyCompanyRepository(CompanyRepository):
    """Async SQLAlchemy implementation of ``CompanyRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> Company:
        model = CompanyModel(**data)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise CompanyConflictError("Company unique constraint violated.") from exc
        await self._session.refresh(model)
        return company_to_entity(model)

    async def get_by_id(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        model = await self._get_model(company_id, include_deleted=include_deleted)
        return company_to_entity(model) if model else None

    async def get_by_slug(
        self,
        company_slug: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        return await self._get_by_attr(
            CompanyModel.company_slug,
            company_slug,
            include_deleted=include_deleted,
        )

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        return await self._get_by_attr(
            CompanyModel.email,
            email,
            include_deleted=include_deleted,
        )

    async def get_by_name(
        self,
        company_name: str,
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        return await self._get_by_attr(
            CompanyModel.company_name,
            company_name,
            include_deleted=include_deleted,
        )

    async def update(
        self,
        company_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Company | None:
        model = await self._get_model(company_id, include_deleted=include_deleted)
        if model is None:
            return None
        for key, value in data.items():
            if hasattr(model, key):
                setattr(model, key, value)
        model.updated_at = datetime.now(UTC)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise CompanyConflictError("Company unique constraint violated.") from exc
        await self._session.refresh(model)
        return company_to_entity(model)

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
        return await self.update(
            company_id,
            {
                "subscription_plan": subscription_plan,
                "max_users": max_users,
                "max_documents": max_documents,
                "max_storage_mb": max_storage_mb,
                "monthly_ai_tokens": monthly_ai_tokens,
                "subscription_expires_at": subscription_expires_at,
            },
        )

    async def update_usage(self, company_id: int, token_usage: int) -> Company | None:
        return await self.update(company_id, {"token_usage": token_usage})

    async def soft_delete(self, company_id: int) -> Company | None:
        model = await self._get_model(company_id, include_deleted=False)
        if model is None:
            return None
        now = datetime.now(UTC)
        model.deleted_at = now
        model.status = CompanyStatus.INACTIVE
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return company_to_entity(model)

    async def archive(self, company_id: int) -> Company | None:
        model = await self._get_model(company_id, include_deleted=True)
        if model is None:
            return None
        now = datetime.now(UTC)
        model.status = CompanyStatus.ARCHIVED
        model.deleted_at = model.deleted_at or now
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return company_to_entity(model)

    async def list_active(self) -> list[Company]:
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.deleted_at.is_(None))
            .where(CompanyModel.status == CompanyStatus.ACTIVE)
            .order_by(CompanyModel.created_at.desc(), CompanyModel.company_id.desc())
        )
        result = await self._session.execute(stmt)
        return [company_to_entity(row) for row in result.scalars().all()]

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
        if sort_by not in SORTABLE_FIELDS:
            raise CompanyValidationError(f"Invalid sort_by '{sort_by}'.")

        filters: list[Any] = []
        if not include_deleted:
            filters.append(CompanyModel.deleted_at.is_(None))
        if company_id is not None:
            filters.append(CompanyModel.company_id == company_id)
        if status is not None:
            filters.append(CompanyModel.status == status)
        if subscription_plan is not None:
            filters.append(CompanyModel.subscription_plan == subscription_plan)
        if search:
            escaped = escape_like(search.strip())
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    CompanyModel.company_name.ilike(pattern, escape="\\"),
                    CompanyModel.company_slug.ilike(pattern, escape="\\"),
                    CompanyModel.email.ilike(pattern, escape="\\"),
                    CompanyModel.legal_name.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = select(func.count()).select_from(CompanyModel)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one())

        stmt: Select[tuple[CompanyModel]] = select(CompanyModel)
        if filters:
            stmt = stmt.where(*filters)

        column = _SORTABLE_COLUMNS[sort_by]
        primary = column.asc() if sort_order.lower() == "asc" else column.desc()
        tie_break = (
            CompanyModel.company_id.asc()
            if sort_order.lower() == "asc"
            else CompanyModel.company_id.desc()
        )
        stmt = stmt.order_by(primary, tie_break)
        stmt = stmt.offset(max(page - 1, 0) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        items = [company_to_entity(row) for row in result.scalars().all()]
        return items, total

    async def _get_by_attr(
        self,
        column: Any,
        value: Any,
        *,
        include_deleted: bool,
    ) -> Company | None:
        stmt = select(CompanyModel).where(column == value)
        if not include_deleted:
            stmt = stmt.where(CompanyModel.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return company_to_entity(model) if model else None

    async def _get_model(
        self,
        company_id: int,
        *,
        include_deleted: bool,
    ) -> CompanyModel | None:
        stmt = select(CompanyModel).where(CompanyModel.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(CompanyModel.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
