"""Role Management Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_name: str = Field(..., min_length=2, max_length=100, examples=["SUPPORT_LEAD"])
    display_name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    company_id: int | None = Field(
        default=None,
        ge=1,
        description="Omit/null for global platform roles (Super Admin only).",
    )
    is_system_role: bool = Field(
        default=False,
        description="System roles may only be created by Super Admin.",
    )
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)


class RoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_name: str | None = Field(default=None, min_length=2, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class RoleStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    company_id: int | None = None
    role_name: str
    display_name: str
    description: str | None = None
    is_system_role: bool
    is_system: bool = False
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_entity(cls, role) -> RoleResponse:
        return cls(
            role_id=role.role_id,
            company_id=role.company_id,
            role_name=role.role_name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_system=role.is_system,
            is_active=role.is_active,
            sort_order=role.sort_order,
            created_at=role.created_at,
            updated_at=role.updated_at,
            deleted_at=role.deleted_at,
        )
