"""Update company subscription use case."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.company import UpdateSubscriptionInput
from app.application.services.company.company_service import CompanyService
from app.domain.entities.company import Company


class UpdateCompanySubscriptionUseCase:
    def __init__(self, session: AsyncSession, service: CompanyService) -> None:
        self._session = session
        self._service = service

    async def execute(
        self,
        company_id: int,
        data: UpdateSubscriptionInput,
        actor: RequestActor,
    ) -> Company:
        try:
            company = await self._service.update_subscription(company_id, data, actor)
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        await self._service.flush_audits()
        return company
