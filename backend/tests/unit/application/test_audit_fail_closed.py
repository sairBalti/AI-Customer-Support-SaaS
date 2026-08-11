"""Fail-closed audit flush lifecycle and DatabaseAuditLogger behavior."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.application.context import RequestActor
from app.application.dto.company import CreateCompanyInput
from app.application.services.company.company_service import CompanyService
from app.application.use_cases.company.create_company import CreateCompanyUseCase
from app.core.audit_sanitize import sanitize_audit_metadata
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.infrastructure.audit.database_audit_logger import DatabaseAuditLogger
from tests.unit.application.test_company_service import InMemoryCompanyRepository


class FailingAuditLogger(AuditLogger):
    def __init__(self) -> None:
        self.calls = 0

    async def log(self, **kwargs: Any) -> None:
        self.calls += 1
        raise RuntimeError("simulated audit persistence failure")


class RecordingThenFailingAudit(AuditLogger):
    """Always fail on emit."""

    async def log(self, **kwargs: Any) -> None:
        raise RuntimeError("audit write failed")


@pytest.mark.asyncio
async def test_flush_audits_keeps_pending_when_persist_fails() -> None:
    repo = InMemoryCompanyRepository()
    audit = FailingAuditLogger()
    service = CompanyService(repo, audit)
    actor = RequestActor(is_super_admin=True, user_id=1)
    await service.create_company(
        CreateCompanyInput(company_name="Fail Closed Co", email="fc@example.com"),
        actor,
    )
    assert len(service._pending_audits) == 1  # noqa: SLF001
    with pytest.raises(RuntimeError, match="simulated audit persistence failure"):
        await service.flush_audits()
    assert len(service._pending_audits) == 1  # noqa: SLF001
    service.discard_audits()
    assert len(service._pending_audits) == 0  # noqa: SLF001


@pytest.mark.asyncio
async def test_create_company_use_case_rolls_back_when_audit_flush_fails() -> None:
    repo = InMemoryCompanyRepository()
    audit = RecordingThenFailingAudit()
    service = CompanyService(repo, audit)
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    use_case = CreateCompanyUseCase(session, service)
    with pytest.raises(RuntimeError, match="audit write failed"):
        await use_case.execute(
            CreateCompanyInput(company_name="Rollback Co", email="rb@example.com"),
            RequestActor(is_super_admin=True, user_id=1),
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited()
    assert service._pending_audits == []  # noqa: SLF001
    assert session.commit.await_count == 0


@pytest.mark.asyncio
async def test_database_audit_logger_propagates_repository_errors() -> None:
    session = AsyncMock()
    logger = DatabaseAuditLogger(session)
    create = AsyncMock(side_effect=RuntimeError("db down"))
    logger._repo = AsyncMock()  # noqa: SLF001
    logger._repo.create = create  # noqa: SLF001
    with pytest.raises(RuntimeError, match="db down"):
        await logger.log(
            action="COMPANY_CREATED",
            entity="companies",
            entity_id=1,
            company_id=1,
            user_id=1,
            metadata={"password": "nope", "token_id": 9},
        )
    assert create.await_count == 1
    payload = create.await_args.args[0]
    assert "password" not in (payload.get("metadata") or {})
    assert payload["metadata"].get("token_id") == 9


def test_sanitize_preserves_token_id_correlation() -> None:
    assert sanitize_audit_metadata({"token_id": 7, "refresh_token": "x"}) == {"token_id": 7}
