"""Company request/response Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan


class CompanyCreateRequest(BaseModel):
    """Payload for ``POST /companies``."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(..., min_length=3, max_length=150, examples=["Acme Corporation"])
    email: EmailStr = Field(..., examples=["admin@acme.com"])
    company_slug: str | None = Field(
        default=None,
        max_length=150,
        description="Optional slug; generated from company_name when omitted.",
        examples=["acme-corporation"],
    )
    legal_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30, examples=["+15551234567"])
    website: str | None = Field(default=None, max_length=255, examples=["https://acme.com"])
    logo_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="UTC", max_length=100, examples=["Asia/Karachi"])
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE
    activate_trial: bool = True
    admin_password: str | None = Field(
        default=None,
        min_length=12,
        max_length=128,
        description="Required for public registration. Creates the first Company Admin login.",
    )
    admin_first_name: str | None = Field(default=None, min_length=2, max_length=100)
    admin_last_name: str | None = Field(default=None, min_length=2, max_length=100)

    @field_validator("company_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CompanyUpdateRequest(BaseModel):
    """Payload for ``PUT /companies/{id}``."""

    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=3, max_length=150)
    legal_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)


class CompanyStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CompanyStatus


class CompanySubscriptionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_plan: SubscriptionPlan
    max_users: int | None = Field(default=None, ge=1)
    max_documents: int | None = Field(default=None, ge=1)
    max_storage_mb: int | None = Field(default=None, ge=1)
    monthly_ai_tokens: int | None = Field(default=None, ge=0)
    subscription_expires_at: datetime | None = None


class CompanyResponse(BaseModel):
    """Public company profile response."""

    model_config = ConfigDict(from_attributes=True)

    company_id: int
    company_name: str
    company_slug: str
    legal_name: str | None = None
    email: EmailStr
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    country: str | None = None
    timezone: str
    subscription_plan: SubscriptionPlan
    status: CompanyStatus
    max_users: int
    max_documents: int
    max_storage_mb: int
    monthly_ai_tokens: int
    token_usage: int
    trial_ends_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
