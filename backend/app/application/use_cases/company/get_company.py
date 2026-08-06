"""Get company use case."""

from __future__ import annotations

from app.application.context import RequestActor
from app.application.services.company.company_service import CompanyService
from app.domain.entities.company import Company


class GetCompanyUseCase:
    def __init__(self, service: CompanyService) -> None:
        self._service = service

    async def execute(self, company_id: int, actor: RequestActor) -> Company:
        return await self._service.get_company(company_id, actor)
