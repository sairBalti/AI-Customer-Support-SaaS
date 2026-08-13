"""Company application DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan


@dataclass(slots=True)
class CreateCompanyInput:
    company_name: str
    email: str
    company_slug: str | None = None
    legal_name: str | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    country: str | None = None
    timezone: str = "UTC"
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE
    activate_trial: bool = True
    # Public onboarding: create Company Admin so the registrant can sign in.
    admin_password: str | None = None
    admin_first_name: str | None = None
    admin_last_name: str | None = None


@dataclass(slots=True)
class UpdateCompanyInput:
    """Partial profile update.

    ``values`` contains only fields present in the request body.
    Explicit JSON nulls are preserved so nullable columns can be cleared.
    """

    values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UpdateCompanyStatusInput:
    status: CompanyStatus


@dataclass(slots=True)
class UpdateSubscriptionInput:
    subscription_plan: SubscriptionPlan
    max_users: int | None = None
    max_documents: int | None = None
    max_storage_mb: int | None = None
    monthly_ai_tokens: int | None = None
    subscription_expires_at: datetime | None = None


@dataclass(slots=True)
class CompanyListQuery:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    status: CompanyStatus | None = None
    subscription_plan: SubscriptionPlan | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    include_deleted: bool = False
