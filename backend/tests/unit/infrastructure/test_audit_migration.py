"""Migration / seed checks for audit_logs + audit.read."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.auth import PermissionModel, RoleModel, RolePermissionModel
from app.infrastructure.database.seed_rbac import seed_rbac


def test_audit_migration_script_is_reversible() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260810_1400_create_audit_logs_table.py"
    )
    spec = importlib.util.spec_from_file_location("audit_mig", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "20260810_1400"
    assert mod.down_revision == "20260810_1000"
    upgrade_src = inspect.getsource(mod.upgrade)
    seed_src = inspect.getsource(mod._seed_audit_permissions)
    downgrade_src = inspect.getsource(mod.downgrade)
    assert "create_table" in upgrade_src
    assert "_seed_audit_permissions" in upgrade_src
    assert "audit.read" in seed_src
    assert "SUPER_ADMIN" in seed_src
    assert "COMPANY_ADMIN" in seed_src
    assert "SUPPORT_MANAGER" in seed_src
    assert "DELETE FROM role_permissions" in downgrade_src
    assert "DELETE FROM permissions" in downgrade_src
    assert "drop_table" in downgrade_src


@pytest.mark.asyncio
async def test_seed_rbac_grants_audit_read_to_admin_roles_only(
    db_session: AsyncSession,
) -> None:
    roles = await seed_rbac(db_session)
    perm = (
        await db_session.execute(
            select(PermissionModel).where(PermissionModel.permission_name == "audit.read")
        )
    ).scalar_one()
    granted = (
        (
            await db_session.execute(
                select(RoleModel.role_name)
                .join(RolePermissionModel, RolePermissionModel.role_id == RoleModel.role_id)
                .where(RolePermissionModel.permission_id == perm.permission_id)
            )
        )
        .scalars()
        .all()
    )
    assert set(granted) == {"SUPER_ADMIN", "COMPANY_ADMIN", "SUPPORT_MANAGER"}
    assert "SUPPORT_AGENT" not in granted
    assert "CUSTOMER" not in granted
    assert roles["COMPANY_ADMIN"]
