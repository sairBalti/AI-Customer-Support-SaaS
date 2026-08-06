"""Company domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan


@dataclass(slots=True)
class Company:
    """Framework-agnostic company tenant entity."""

    company_id: int
    company_name: str
    company_slug: str
    email: str
    timezone: str
    subscription_plan: SubscriptionPlan
    status: CompanyStatus
    max_users: int
    max_documents: int
    max_storage_mb: int
    monthly_ai_tokens: int
    token_usage: int
    created_at: datetime
    updated_at: datetime
    legal_name: str | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    country: str | None = None
    trial_ends_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    last_activity_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
