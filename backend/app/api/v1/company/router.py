"""Company API router.

Authz summary (OpenAPI BearerAuth on protected routes):

| Method | Path | Access |
|--------|------|--------|
| POST | `/companies` | Public (registration) |
| GET | `/companies` | JWT + `companies.read` |
| GET | `/companies/{id}` | JWT + `companies.read` (tenant-scoped) |
| PUT | `/companies/{id}` | JWT + `companies.update` (tenant-scoped) |
| PATCH | `/companies/{id}/status` | JWT + `companies.manage` |
| PATCH | `/companies/{id}/subscription` | JWT + `companies.manage` |
| DELETE | `/companies/{id}` | JWT + `companies.manage` |
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CompanyServiceDep, DbSession, RequestActorDep
from app.api.security import RequireCompanyManage, RequireCompanyRead, RequireCompanyUpdate
from app.api.v1.company.schemas import (
    CompanyCreateRequest,
    CompanyResponse,
    CompanyStatusUpdateRequest,
    CompanySubscriptionUpdateRequest,
    CompanyUpdateRequest,
)
from app.application.dto.company import (
    CompanyListQuery,
    CreateCompanyInput,
    UpdateCompanyInput,
    UpdateCompanyStatusInput,
    UpdateSubscriptionInput,
)
from app.application.use_cases.company.create_company import CreateCompanyUseCase
from app.application.use_cases.company.get_company import GetCompanyUseCase
from app.application.use_cases.company.list_companies import ListCompaniesUseCase
from app.application.use_cases.company.soft_delete_company import SoftDeleteCompanyUseCase
from app.application.use_cases.company.update_company import UpdateCompanyUseCase
from app.application.use_cases.company.update_company_status import UpdateCompanyStatusUseCase
from app.application.use_cases.company.update_company_subscription import (
    UpdateCompanySubscriptionUseCase,
)
from app.core.pagination import Page
from app.core.responses.envelopes import success_envelope
from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan

router = APIRouter(prefix="/companies", tags=["Companies"])


def _to_response(company: Company) -> CompanyResponse:
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Register a company",
    description="Public company registration / onboarding. No JWT required.",
    response_description="Created company profile",
    responses={409: {"description": "Unique constraint conflict"}},
)
async def create_company(
    body: CompanyCreateRequest,
    session: DbSession,
    service: CompanyServiceDep,
    actor: RequestActorDep,
) -> dict[str, Any]:
    """Create a tenant company during onboarding (public)."""
    use_case = CreateCompanyUseCase(session, service)
    company = await use_case.execute(
        CreateCompanyInput(**body.model_dump()),
        actor,
    )
    return success_envelope(_to_response(company).model_dump(mode="json"), message="Company created.")


@router.get(
    "",
    summary="List companies",
    description="Requires Bearer JWT and `companies.read`. Non–Super Admin see own tenant only.",
    response_description="Paginated company list",
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Insufficient permission or inactive company"},
    },
)
async def list_companies(
    service: CompanyServiceDep,
    actor: RequireCompanyRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(description="Search name, slug, email")] = None,
    status_filter: Annotated[
        CompanyStatus | None,
        Query(alias="status", description="Filter by status"),
    ] = None,
    subscription_plan: Annotated[SubscriptionPlan | None, Query()] = None,
    sort_by: Annotated[
        str,
        Query(
            description=(
                "Sort field: created_at, updated_at, company_name, status, "
                "subscription_plan, last_activity_at, subscription_expires_at"
            ),
        ),
    ] = "created_at",
    sort_order: Annotated[str, Query(pattern="^(?i)(asc|desc)$")] = "desc",
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """List companies with pagination, filtering, sorting, and search."""
    use_case = ListCompaniesUseCase(service)
    items, total = await use_case.execute(
        CompanyListQuery(
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
            subscription_plan=subscription_plan,
            sort_by=sort_by,
            sort_order=sort_order.lower(),
            include_deleted=include_deleted,
        ),
        actor,
    )
    page_data = Page.of(
        [_to_response(item).model_dump(mode="json") for item in items],
        page=page,
        page_size=page_size,
        total_items=total,
    )
    return success_envelope(page_data.model_dump(mode="json"))


@router.get(
    "/{company_id}",
    summary="Get company by ID",
    description="Requires Bearer JWT and `companies.read`. Tenant isolation enforced.",
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Cross-tenant access denied or insufficient permission"},
        404: {"description": "Company not found"},
    },
)
async def get_company(
    company_id: Annotated[int, Path(ge=1)],
    service: CompanyServiceDep,
    actor: RequireCompanyRead,
) -> dict[str, Any]:
    """Retrieve a company profile (tenant-scoped)."""
    company = await GetCompanyUseCase(service).execute(company_id, actor)
    return success_envelope(_to_response(company).model_dump(mode="json"))


@router.put(
    "/{company_id}",
    summary="Update company profile",
    description="Requires Bearer JWT and `companies.update`. Tenant isolation enforced.",
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Cross-tenant access denied or insufficient permission"},
    },
)
async def update_company(
    company_id: Annotated[int, Path(ge=1)],
    body: CompanyUpdateRequest,
    session: DbSession,
    service: CompanyServiceDep,
    actor: RequireCompanyUpdate,
) -> dict[str, Any]:
    """Update mutable company profile fields."""
    use_case = UpdateCompanyUseCase(session, service)
    company = await use_case.execute(
        company_id,
        UpdateCompanyInput(values=body.model_dump(exclude_unset=True)),
        actor,
    )
    return success_envelope(_to_response(company).model_dump(mode="json"), message="Company updated.")


@router.patch(
    "/{company_id}/status",
    summary="Update company status",
    description=(
        "Admin-only. Requires Bearer JWT and `companies.manage`. "
        "Company Admin is limited to their own company; Super Admin may manage any."
    ),
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Insufficient permission or cross-tenant denial"},
    },
)
async def update_company_status(
    company_id: Annotated[int, Path(ge=1)],
    body: CompanyStatusUpdateRequest,
    session: DbSession,
    service: CompanyServiceDep,
    actor: RequireCompanyManage,
) -> dict[str, Any]:
    """Change company lifecycle status (manage permission)."""
    use_case = UpdateCompanyStatusUseCase(session, service)
    company = await use_case.execute(
        company_id,
        UpdateCompanyStatusInput(status=body.status),
        actor,
    )
    return success_envelope(_to_response(company).model_dump(mode="json"))


@router.patch(
    "/{company_id}/subscription",
    summary="Update company subscription",
    description=(
        "Admin-only. Requires Bearer JWT and `companies.manage`. "
        "Company Admin is limited to their own company; Super Admin may manage any."
    ),
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Insufficient permission or cross-tenant denial"},
    },
)
async def update_company_subscription(
    company_id: Annotated[int, Path(ge=1)],
    body: CompanySubscriptionUpdateRequest,
    session: DbSession,
    service: CompanyServiceDep,
    actor: RequireCompanyManage,
) -> dict[str, Any]:
    """Change plan and quotas (manage permission; audited)."""
    use_case = UpdateCompanySubscriptionUseCase(session, service)
    company = await use_case.execute(
        company_id,
        UpdateSubscriptionInput(**body.model_dump()),
        actor,
    )
    return success_envelope(_to_response(company).model_dump(mode="json"))


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete company",
    description=(
        "Admin-only soft-delete. Requires Bearer JWT and `companies.manage`. "
        "Never hard-deletes."
    ),
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Insufficient permission or cross-tenant denial"},
    },
)
async def soft_delete_company(
    company_id: Annotated[int, Path(ge=1)],
    session: DbSession,
    service: CompanyServiceDep,
    actor: RequireCompanyManage,
) -> dict[str, Any]:
    """Soft-delete a company (manage permission). Never hard-deletes."""
    use_case = SoftDeleteCompanyUseCase(session, service)
    company = await use_case.execute(company_id, actor)
    return success_envelope(
        _to_response(company).model_dump(mode="json"),
        message="Company soft-deleted.",
    )
