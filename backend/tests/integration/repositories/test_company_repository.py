"""Integration tests for SQLAlchemy company repository."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.infrastructure.database.repositories.company_repository import (
    SQLAlchemyCompanyRepository,
)


@pytest.mark.asyncio
async def test_repository_create_search_and_soft_delete(db_session: AsyncSession) -> None:
    repo = SQLAlchemyCompanyRepository(db_session)
    created = await repo.create(
        {
            "company_name": "Gamma Inc",
            "company_slug": "gamma-inc",
            "email": "hello@gamma.com",
            "timezone": "UTC",
            "subscription_plan": SubscriptionPlan.FREE,
            "status": CompanyStatus.ACTIVE,
            "max_users": 5,
            "max_documents": 50,
            "max_storage_mb": 500,
            "monthly_ai_tokens": 100000,
            "token_usage": 0,
        }
    )
    await db_session.commit()

    assert created.company_id > 0
    fetched = await repo.get_by_slug("gamma-inc")
    assert fetched is not None
    assert fetched.email == "hello@gamma.com"

    items, total = await repo.search(search="gamma", page=1, page_size=10)
    assert total == 1
    assert items[0].company_slug == "gamma-inc"

    deleted = await repo.soft_delete(created.company_id)
    await db_session.commit()
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert await repo.get_by_id(created.company_id) is None
