"""List companies use case."""

from __future__ import annotations

from app.application.context import RequestActor
from app.application.dto.company import CompanyListQuery
from app.application.services.company.company_service import CompanyService
from app.domain.entities.company import Company


class ListCompaniesUseCase:
    def __init__(self, service: CompanyService) -> None:
        self._service = service

    async def execute(
        self,
        query: CompanyListQuery,
        actor: RequestActor,
    ) -> tuple[list[Company], int]:
        return await self._service.list_companies(query, actor)
