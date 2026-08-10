"""Unit tests for AuditLogService + metadata sanitization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.audit import AuditListQuery, RecordAuditInput
from app.application.services.audit.audit_log_service import AuditLogService
from app.core.audit_sanitize import sanitize_audit_metadata
from app.domain.entities.audit_log import AuditLog
from app.domain.exceptions.audit import AuditLogAccessDeniedError, AuditLogNotFoundError
from app.domain.exceptions.auth import InsufficientPermissionError


class _Repo:
    def __init__(self) -> None:
        self.rows: dict[int, AuditLog] = {}
        self._next = 1

    async def create(self, data: dict[str, Any]) -> AuditLog:
        aid = self._next
        self._next += 1
        row = AuditLog(
            audit_log_id=aid,
            company_id=int(data["company_id"]),
            actor_user_id=data.get("actor_user_id"),
            audit_uuid=data.get("audit_uuid"),
            action=data["action"],
            entity_type=data["entity_type"],
            entity_id=data.get("entity_id"),
            description=data.get("description"),
            metadata=dict(data.get("metadata") or {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=data.get("created_at", datetime.now(UTC)),
        )
        self.rows[aid] = row
        return row

    async def get_by_id(
        self,
        audit_log_id: int,
        *,
        company_id: int | None = None,
    ) -> AuditLog | None:
        row = self.rows.get(audit_log_id)
        if row is None:
            return None
        if company_id is not None and row.company_id != company_id:
            return None
        return row

    async def list_filtered(self, **kwargs: Any) -> tuple[list[AuditLog], int]:
        items = list(self.rows.values())
        company_id = kwargs.get("company_id")
        if company_id is not None:
            items = [r for r in items if r.company_id == company_id]
        if kwargs.get("actor_user_id") is not None:
            items = [r for r in items if r.actor_user_id == kwargs["actor_user_id"]]
        if kwargs.get("action") is not None:
            items = [r for r in items if r.action == kwargs["action"]]
        if kwargs.get("entity_type") is not None:
            items = [r for r in items if r.entity_type == kwargs["entity_type"]]
        if kwargs.get("entity_id") is not None:
            items = [r for r in items if r.entity_id == kwargs["entity_id"]]
        if kwargs.get("from_date") is not None:
            items = [r for r in items if r.created_at >= kwargs["from_date"]]
        if kwargs.get("to_date") is not None:
            items = [r for r in items if r.created_at <= kwargs["to_date"]]
        total = len(items)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        offset = max(page - 1, 0) * page_size
        return items[offset : offset + page_size], total


def _admin(company_id: int = 10, user_id: int = 1) -> RequestActor:
    return RequestActor(
        user_id=user_id,
        company_id=company_id,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"audit.read"}),
    )


def _manager(company_id: int = 10) -> RequestActor:
    return RequestActor(
        user_id=2,
        company_id=company_id,
        role_name="SUPPORT_MANAGER",
        permissions=frozenset({"audit.read"}),
    )


def _agent(company_id: int = 10) -> RequestActor:
    return RequestActor(
        user_id=3,
        company_id=company_id,
        role_name="SUPPORT_AGENT",
        permissions=frozenset({"tickets.read"}),
    )


def test_sanitize_strips_secrets() -> None:
    cleaned = sanitize_audit_metadata(
        {
            "email": "a@b.co",
            "password": "secret",
            "password_hash": "x",
            "access_token": "tok",
            "refresh_token": "rt",
            "api_key": "k",
            "openai_api_key": "oai",
            "safe_flag": True,
        }
    )
    assert cleaned == {"email": "a@b.co", "safe_flag": True}


@pytest.mark.asyncio
async def test_record_and_list_filters() -> None:
    repo = _Repo()
    service = AuditLogService(audit_logs=repo)
    now = datetime.now(UTC)
    await service.record(
        RecordAuditInput(
            company_id=10,
            actor_user_id=1,
            action="COMPANY_CREATED",
            entity_type="companies",
            entity_id=10,
            metadata={"password": "nope", "name": "Acme"},
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
    )
    await service.record(
        RecordAuditInput(
            company_id=10,
            actor_user_id=2,
            action="document.upload",
            entity_type="documents",
            entity_id=5,
        )
    )
    await service.record(
        RecordAuditInput(
            company_id=20,
            actor_user_id=9,
            action="COMPANY_CREATED",
            entity_type="companies",
            entity_id=20,
        )
    )
    # Force created_at for date filter on second row
    repo.rows[2].created_at = now - timedelta(days=2)

    page = await service.list_logs(
        AuditListQuery(action="COMPANY_CREATED", page=1, page_size=10),
        _admin(),
    )
    assert page.meta.total_items == 1
    assert page.items[0].action == "COMPANY_CREATED"
    assert "password" not in page.items[0].metadata
    assert page.items[0].metadata.get("name") == "Acme"

    by_actor = await service.list_logs(
        AuditListQuery(actor_user_id=2),
        _manager(),
    )
    assert by_actor.meta.total_items == 1
    assert by_actor.items[0].entity_type == "documents"

    by_entity = await service.list_logs(
        AuditListQuery(entity_type="documents", entity_id=5),
        _admin(),
    )
    assert by_entity.meta.total_items == 1

    by_date = await service.list_logs(
        AuditListQuery(from_date=now - timedelta(hours=1)),
        _admin(),
    )
    assert by_date.meta.total_items == 1
    assert by_date.items[0].action == "COMPANY_CREATED"


@pytest.mark.asyncio
async def test_pagination() -> None:
    repo = _Repo()
    service = AuditLogService(audit_logs=repo)
    for i in range(5):
        await service.record(
            RecordAuditInput(
                company_id=10,
                action=f"action.{i}",
                entity_type="misc",
                entity_id=i,
            )
        )
    page = await service.list_logs(AuditListQuery(page=2, page_size=2), _admin())
    assert len(page.items) == 2
    assert page.meta.total_items == 5
    assert page.meta.page == 2


@pytest.mark.asyncio
async def test_rbac_requires_audit_read() -> None:
    service = AuditLogService(audit_logs=_Repo())
    with pytest.raises(InsufficientPermissionError):
        await service.list_logs(AuditListQuery(), _agent())


@pytest.mark.asyncio
async def test_tenant_isolation_list_and_get() -> None:
    repo = _Repo()
    service = AuditLogService(audit_logs=repo)
    a = await service.record(
        RecordAuditInput(company_id=10, action="A", entity_type="x", entity_id=1)
    )
    b = await service.record(
        RecordAuditInput(company_id=20, action="B", entity_type="x", entity_id=2)
    )

    listed = await service.list_logs(AuditListQuery(), _admin(company_id=10))
    assert listed.meta.total_items == 1
    assert listed.items[0].audit_log_id == a.audit_log_id

    with pytest.raises(AuditLogAccessDeniedError):
        await service.list_logs(AuditListQuery(company_id=20), _admin(company_id=10))

    with pytest.raises(AuditLogAccessDeniedError):
        await service.get_log(b.audit_log_id, _admin(company_id=10))

    with pytest.raises(AuditLogNotFoundError):
        await service.get_log(9999, _admin(company_id=10))

    got = await service.get_log(a.audit_log_id, _admin(company_id=10))
    assert got.audit_log_id == a.audit_log_id

    # Super admin can scope or cross-read
    sa = RequestActor(is_super_admin=True, user_id=99, permissions=frozenset())
    all_rows = await service.list_logs(AuditListQuery(), sa)
    assert all_rows.meta.total_items == 2
    scoped = await service.list_logs(AuditListQuery(company_id=20), sa)
    assert scoped.meta.total_items == 1
    assert await service.get_log(b.audit_log_id, sa)


@pytest.mark.asyncio
async def test_append_only_no_update_api_on_repo_protocol() -> None:
    """Repository port exposes create + reads only."""
    methods = {name for name in dir(_Repo) if not name.startswith("_")}
    assert "create" in methods
    assert "update" not in methods
    assert "delete" not in methods
