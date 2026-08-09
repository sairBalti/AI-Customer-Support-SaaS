"""Seed helpers for RBAC baseline (roles/permissions) used in tests."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.auth import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)


async def seed_rbac(session: AsyncSession) -> dict[str, int]:
    """Insert default global system roles/permissions if empty."""
    existing = (await session.execute(select(RoleModel.role_id).limit(1))).first()
    if existing:
        rows = (await session.execute(select(RoleModel))).scalars().all()
        return {r.role_name: int(r.role_id) for r in rows}

    roles = [
        RoleModel(
            role_name="SUPER_ADMIN",
            display_name="Super Admin",
            company_id=None,
            is_system_role=True,
            sort_order=1,
        ),
        RoleModel(
            role_name="COMPANY_ADMIN",
            display_name="Company Admin",
            company_id=None,
            is_system_role=True,
            sort_order=2,
        ),
        RoleModel(
            role_name="SUPPORT_MANAGER",
            display_name="Support Manager",
            company_id=None,
            is_system_role=True,
            sort_order=3,
        ),
        RoleModel(
            role_name="SUPPORT_AGENT",
            display_name="Support Agent",
            company_id=None,
            is_system_role=True,
            sort_order=4,
        ),
        RoleModel(
            role_name="CUSTOMER",
            display_name="Customer",
            company_id=None,
            is_system_role=True,
            sort_order=5,
        ),
    ]
    session.add_all(roles)
    await session.flush()

    perm_names = [
        ("auth.login", "auth", "login"),
        ("auth.logout", "auth", "logout"),
        ("auth.refresh", "auth", "refresh"),
        ("companies.read", "companies", "read"),
        ("companies.update", "companies", "update"),
        ("companies.manage", "companies", "manage"),
        ("users.create", "users", "create"),
        ("users.read", "users", "read"),
        ("users.update", "users", "update"),
        ("users.delete", "users", "delete"),
        ("roles.create", "roles", "create"),
        ("roles.read", "roles", "read"),
        ("roles.update", "roles", "update"),
        ("roles.delete", "roles", "delete"),
        ("documents.upload", "documents", "upload"),
        ("documents.read", "documents", "read"),
        ("documents.update", "documents", "update"),
        ("documents.delete", "documents", "delete"),
        ("documents.reindex", "documents", "reindex"),
        ("knowledge.process", "knowledge", "process"),
        ("knowledge.search", "knowledge", "search"),
    ]
    perms = [PermissionModel(permission_name=n, module=m, action=a) for n, m, a in perm_names]
    session.add_all(perms)
    await session.flush()

    role_map = {r.role_name: int(r.role_id) for r in roles}
    for perm in perms:
        session.add(
            RolePermissionModel(role_id=role_map["SUPER_ADMIN"], permission_id=perm.permission_id)
        )
        name = perm.permission_name
        if name.startswith(("auth.", "companies.", "users.", "roles.", "documents.", "knowledge.")):
            session.add(
                RolePermissionModel(
                    role_id=role_map["COMPANY_ADMIN"],
                    permission_id=perm.permission_id,
                )
            )
        if name.startswith("auth."):
            for rn in ("CUSTOMER", "SUPPORT_AGENT", "SUPPORT_MANAGER"):
                session.add(
                    RolePermissionModel(role_id=role_map[rn], permission_id=perm.permission_id)
                )
        if name in {
            "documents.upload",
            "documents.read",
            "documents.update",
            "documents.reindex",
            "knowledge.process",
            "knowledge.search",
        }:
            session.add(
                RolePermissionModel(
                    role_id=role_map["SUPPORT_MANAGER"],
                    permission_id=perm.permission_id,
                )
            )
        if name in {"documents.read", "knowledge.search"}:
            session.add(
                RolePermissionModel(
                    role_id=role_map["SUPPORT_AGENT"],
                    permission_id=perm.permission_id,
                )
            )
    await session.flush()
    return role_map
