"""Integration tests for audit log API, RBAC, isolation, and event emission."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.auth import UserModel
from app.infrastructure.database.models.company import CompanyModel
from app.infrastructure.database.seed_rbac import seed_rbac


@pytest.fixture
async def audit_seed(db_session: AsyncSession, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hashing")
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "chroma")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    from app.core.config.settings import get_settings

    get_settings.cache_clear()

    roles = await seed_rbac(db_session)
    company_a = CompanyModel(
        company_name="Audit A",
        company_slug="audit-a",
        email="ops@audit-a.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    company_b = CompanyModel(
        company_name="Audit B",
        company_slug="audit-b",
        email="ops@audit-b.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    platform = CompanyModel(
        company_name="Platform Audit",
        company_slug="platform-audit",
        email="root@platform-audit.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        status=CompanyStatus.ACTIVE,
        max_users=100,
        max_documents=1000,
        max_storage_mb=10000,
        monthly_ai_tokens=1_000_000,
        token_usage=0,
    )
    db_session.add_all([company_a, company_b, platform])
    await db_session.flush()
    password = "Str0ng!Password"
    hashed = hash_password(password)
    users = {
        "admin_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["COMPANY_ADMIN"],
            first_name="Ada",
            last_name="Admin",
            email="admin@audit-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "manager_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["SUPPORT_MANAGER"],
            first_name="Mia",
            last_name="Manager",
            email="manager@audit-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "agent_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["SUPPORT_AGENT"],
            first_name="Eve",
            last_name="Agent",
            email="agent@audit-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "cust_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["CUSTOMER"],
            first_name="Ann",
            last_name="Customer",
            email="cust@audit-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "admin_b": UserModel(
            company_id=company_b.company_id,
            role_id=roles["COMPANY_ADMIN"],
            first_name="Bea",
            last_name="Admin",
            email="admin@audit-b.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "super": UserModel(
            company_id=platform.company_id,
            role_id=roles["SUPER_ADMIN"],
            first_name="Sue",
            last_name="Admin",
            email="super@platform-audit.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
    }
    db_session.add_all(list(users.values()))
    await db_session.commit()
    return {
        "password": password,
        "emails": {k: v.email for k, v in users.items()},
        "user_ids": {k: int(v.user_id) for k, v in users.items()},
        "company_a_id": int(company_a.company_id),
        "company_b_id": int(company_b.company_id),
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(api_client: AsyncClient, email: str, password: str) -> dict:
    resp = await api_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _token(api_client: AsyncClient, email: str, password: str) -> str:
    return (await _login(api_client, email, password))["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_audit_rbac_and_read_only(
    api_client: AsyncClient,
    audit_seed: dict,
) -> None:
    admin = await _token(api_client, audit_seed["emails"]["admin_a"], audit_seed["password"])
    manager = await _token(api_client, audit_seed["emails"]["manager_a"], audit_seed["password"])
    agent = await _token(api_client, audit_seed["emails"]["agent_a"], audit_seed["password"])
    customer = await _token(api_client, audit_seed["emails"]["cust_a"], audit_seed["password"])

    assert (await api_client.get("/api/v1/audit-logs", headers=_auth(admin))).status_code == 200
    assert (await api_client.get("/api/v1/audit-logs", headers=_auth(manager))).status_code == 200
    assert (await api_client.get("/api/v1/audit-logs", headers=_auth(agent))).status_code == 403
    assert (await api_client.get("/api/v1/audit-logs", headers=_auth(customer))).status_code == 403

    assert (
        await api_client.post("/api/v1/audit-logs", headers=_auth(admin), json={})
    ).status_code in {
        405,
        404,
        422,
    }
    assert (await api_client.delete("/api/v1/audit-logs/1", headers=_auth(admin))).status_code in {
        405,
        404,
    }


@pytest.mark.asyncio
async def test_company_ops_emit_audit_and_isolation(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    super_tok = await _token(api_client, audit_seed["emails"]["super"], audit_seed["password"])
    admin_a = await _token(api_client, audit_seed["emails"]["admin_a"], audit_seed["password"])
    admin_b = await _token(api_client, audit_seed["emails"]["admin_b"], audit_seed["password"])

    created = await api_client.post(
        "/api/v1/companies",
        json={
            "company_name": "Fresh Audit Co",
            "company_slug": "fresh-audit-co",
            "email": "hello@fresh-audit.co",
            "timezone": "UTC",
            "admin_password": "Str0ng!Password",
            "admin_first_name": "Fresh",
            "admin_last_name": "Admin",
        },
    )
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["company_id"]

    # Company-scoped admin of the new tenant is not seeded; verify create audit via Super Admin
    create_audits = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(super_tok),
        params={"action": "COMPANY_CREATED", "entity_id": new_id},
    )
    assert create_audits.status_code == 200
    assert create_audits.json()["data"]["meta"]["total_items"] >= 1

    status_resp = await api_client.patch(
        f"/api/v1/companies/{new_id}/status",
        headers=_auth(super_tok),
        json={"status": "SUSPENDED"},
    )
    assert status_resp.status_code == 200, status_resp.text

    status_audits = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(super_tok),
        params={"action": "COMPANY_STATUS_CHANGED", "entity_id": new_id},
    )
    assert status_audits.status_code == 200
    assert status_audits.json()["data"]["meta"]["total_items"] >= 1

    listed_a = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin_a),
        params={"action": "USER_LOGIN"},
    )
    assert listed_a.status_code == 200
    for item in listed_a.json()["data"]["items"]:
        assert item["company_id"] == audit_seed["company_a_id"]

    # Seed a row in B and ensure A cannot read it by id
    db_session.add(
        AuditLogModel(
            company_id=audit_seed["company_b_id"],
            actor_user_id=audit_seed["user_ids"]["admin_b"],
            audit_uuid="11111111-1111-1111-1111-111111111111",
            action="COMPANY_UPDATED",
            entity_type="companies",
            entity_id=audit_seed["company_b_id"],
            metadata_={"note": "b-only"},
        )
    )
    await db_session.commit()
    b_row = (
        await db_session.execute(
            select(AuditLogModel).where(
                AuditLogModel.audit_uuid == "11111111-1111-1111-1111-111111111111"
            )
        )
    ).scalar_one()

    denied = await api_client.get(
        f"/api/v1/audit-logs/{b_row.audit_log_id}",
        headers=_auth(admin_a),
    )
    assert denied.status_code == 404
    # Response must not reveal whether the foreign ID exists.
    assert denied.json()["error"]["code"] == "AUDIT_LOG_NOT_FOUND"

    missing = await api_client.get(
        "/api/v1/audit-logs/99999999",
        headers=_auth(admin_a),
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "AUDIT_LOG_NOT_FOUND"

    # Tenant cannot filter by another company's id via query param
    bypass = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin_a),
        params={"company_id": audit_seed["company_b_id"]},
    )
    assert bypass.status_code == 403

    allowed_b = await api_client.get(
        f"/api/v1/audit-logs/{b_row.audit_log_id}",
        headers=_auth(admin_b),
    )
    assert allowed_b.status_code == 200
    assert allowed_b.json()["data"]["company_id"] == audit_seed["company_b_id"]
    assert allowed_b.json()["data"]["audit_uuid"] == "11111111-1111-1111-1111-111111111111"

    # Super Admin can read foreign-company row by id
    sa_get = await api_client.get(
        f"/api/v1/audit-logs/{b_row.audit_log_id}",
        headers=_auth(super_tok),
    )
    assert sa_get.status_code == 200
    assert sa_get.json()["data"]["company_id"] == audit_seed["company_b_id"]

    # Listing as A must not include B rows even when filtering entity_id
    cross = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin_a),
        params={"entity_id": audit_seed["company_b_id"]},
    )
    assert cross.status_code == 200
    assert all(i["company_id"] == audit_seed["company_a_id"] for i in cross.json()["data"]["items"])

    # Super admin can filter by company
    sa_list = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(super_tok),
        params={"company_id": audit_seed["company_b_id"]},
    )
    assert sa_list.status_code == 200
    assert sa_list.json()["data"]["meta"]["total_items"] >= 1


@pytest.mark.asyncio
async def test_document_chat_ticket_role_audits_and_no_secrets(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    admin = await _token(api_client, audit_seed["emails"]["admin_a"], audit_seed["password"])
    cust = await _token(api_client, audit_seed["emails"]["cust_a"], audit_seed["password"])
    agent = await _token(api_client, audit_seed["emails"]["agent_a"], audit_seed["password"])

    # Document upload
    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(admin),
        files={"file": ("notes.txt", b"refund policy text", "text/plain")},
        data={"document_name": "Notes"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    # Role create (company-scoped)
    role = await api_client.post(
        "/api/v1/roles",
        headers=_auth(admin),
        json={
            "role_name": "audit_helper",
            "display_name": "Audit Helper",
            "description": "Helper role for audit tests",
        },
    )
    assert role.status_code == 201, role.text

    # Chat conversation + message
    conv = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "Help please"},
    )
    assert conv.status_code == 201, conv.text
    conversation_id = conv.json()["data"]["conversation_id"]

    msg = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=_auth(cust),
        json={"content": "How do refunds work?"},
    )
    assert msg.status_code == 200, msg.text

    # Ticket
    ticket = await api_client.post(
        "/api/v1/tickets",
        headers=_auth(cust),
        json={
            "subject": "Need human",
            "description": "Still stuck",
            "priority": "MEDIUM",
            "category": "ACCOUNT",
        },
    )
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["data"]["ticket_id"]

    assigned = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=_auth(admin),
        json={"assigned_to": audit_seed["user_ids"]["agent_a"]},
    )
    assert assigned.status_code == 200, assigned.text

    resolved = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/resolve",
        headers=_auth(agent),
    )
    assert resolved.status_code == 200, resolved.text

    closed = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/close",
        headers=_auth(admin),
    )
    assert closed.status_code == 200, closed.text

    rows = (
        (
            await db_session.execute(
                select(AuditLogModel).where(AuditLogModel.company_id == audit_seed["company_a_id"])
            )
        )
        .scalars()
        .all()
    )
    actions = {r.action for r in rows}
    assert "document.upload" in actions
    assert "chat.conversation.create" in actions
    assert "chat.message.send" in actions
    assert "tickets.create" in actions
    assert "tickets.assign" in actions
    assert "tickets.resolve" in actions
    assert "tickets.close" in actions
    assert "ROLE_CREATED" in actions

    # Filters via API
    docs = await api_client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={"entity_type": "documents", "entity_id": doc_id},
    )
    assert docs.status_code == 200
    assert docs.json()["data"]["meta"]["total_items"] >= 1

    # Reading audit logs must not generate more audit rows
    before = len(rows)
    await api_client.get("/api/v1/audit-logs", headers=_auth(admin))
    after_rows = (
        (
            await db_session.execute(
                select(AuditLogModel).where(AuditLogModel.company_id == audit_seed["company_a_id"])
            )
        )
        .scalars()
        .all()
    )
    assert len(after_rows) == before

    # No secrets stored in any metadata
    for r in after_rows:
        meta = r.metadata_ or {}
        lowered = {str(k).lower() for k in meta}
        assert "password" not in lowered
        assert "access_token" not in lowered
        assert "refresh_token" not in lowered
        assert "api_key" not in lowered


@pytest.mark.asyncio
async def test_auth_login_failed_refresh_logout_audits(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    email = audit_seed["emails"]["admin_a"]
    password = audit_seed["password"]

    failed = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!!"},
    )
    assert failed.status_code == 401

    login = await _login(api_client, email, password)
    access = login["tokens"]["access_token"]
    refresh = login["tokens"]["refresh_token"]

    refreshed = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_refresh = refreshed.json()["data"]["tokens"]["refresh_token"]

    logout = await api_client.post(
        "/api/v1/auth/logout",
        headers=_auth(access),
        json={"refresh_token": new_refresh},
    )
    assert logout.status_code == 200, logout.text

    rows = (
        (
            await db_session.execute(
                select(AuditLogModel).where(AuditLogModel.company_id == audit_seed["company_a_id"])
            )
        )
        .scalars()
        .all()
    )
    actions = {r.action for r in rows}
    assert "USER_LOGIN_FAILED" in actions
    assert "USER_LOGIN" in actions
    assert "TOKEN_REFRESHED" in actions
    assert "USER_LOGOUT" in actions

    for row in rows:
        if row.action == "TOKEN_REFRESHED":
            assert "token_id" in (row.metadata_ or {})
            assert "refresh_token" not in (row.metadata_ or {})
            assert "access_token" not in (row.metadata_ or {})


@pytest.mark.asyncio
async def test_ticket_update_and_escalate_audits(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    admin = await _token(api_client, audit_seed["emails"]["admin_a"], audit_seed["password"])
    cust = await _token(api_client, audit_seed["emails"]["cust_a"], audit_seed["password"])

    ticket = await api_client.post(
        "/api/v1/tickets",
        headers=_auth(cust),
        json={
            "subject": "Update me",
            "description": "desc",
            "priority": "LOW",
            "category": "ACCOUNT",
        },
    )
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["data"]["ticket_id"]

    updated = await api_client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=_auth(admin),
        json={"priority": "HIGH"},
    )
    assert updated.status_code == 200, updated.text

    conv = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "Escalate path"},
    )
    assert conv.status_code == 201, conv.text
    conversation_id = conv.json()["data"]["conversation_id"]

    escalated = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/ticket",
        headers=_auth(cust),
        json={
            "subject": "Needs human",
            "description": "from chat",
            "priority": "MEDIUM",
            "category": "TECHNICAL",
        },
    )
    assert escalated.status_code == 201, escalated.text

    actions = {
        r.action
        for r in (
            await db_session.execute(
                select(AuditLogModel).where(AuditLogModel.company_id == audit_seed["company_a_id"])
            )
        )
        .scalars()
        .all()
    }
    assert "tickets.update" in actions
    assert "tickets.escalate_from_chat" in actions


@pytest.mark.asyncio
async def test_knowledge_process_reindex_deindex_audits(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    admin = await _token(api_client, audit_seed["emails"]["admin_a"], audit_seed["password"])

    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(admin),
        files={
            "file": (
                "policy.txt",
                b"Refund policy allows returns within thirty days for defective items.",
                "text/plain",
            )
        },
        data={"document_name": "Policy"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    processed = await api_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=_auth(admin),
    )
    assert processed.status_code == 200, processed.text

    reindexed = await api_client.post(
        f"/api/v1/documents/{doc_id}/reindex",
        headers=_auth(admin),
    )
    assert reindexed.status_code == 200, reindexed.text

    deleted = await api_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=_auth(admin),
    )
    assert deleted.status_code == 200, deleted.text

    actions = {
        r.action
        for r in (
            await db_session.execute(
                select(AuditLogModel).where(AuditLogModel.company_id == audit_seed["company_a_id"])
            )
        )
        .scalars()
        .all()
    }
    assert "knowledge.process" in actions
    assert "knowledge.reindex" in actions
    assert "knowledge.deindex" in actions
    assert "document.delete" in actions


@pytest.mark.asyncio
async def test_fail_closed_audit_logger_blocks_company_create(
    api_client: AsyncClient,
    audit_seed: dict,
    db_session: AsyncSession,
) -> None:
    """Override audit logger so persistence raises; create must not succeed."""
    from app.api.deps import get_audit_logger
    from app.domain.interfaces.services.audit_logger import AuditLogger

    class Boom(AuditLogger):
        async def log(self, **kwargs: Any) -> None:
            if kwargs.get("company_id") is not None:
                raise RuntimeError("forced audit failure")

    app = api_client._transport.app  # type: ignore[attr-defined]  # noqa: SLF001
    app.dependency_overrides[get_audit_logger] = lambda: Boom()
    try:
        before = (
            await db_session.execute(
                select(AuditLogModel.action).where(
                    AuditLogModel.action == "COMPANY_CREATED",
                )
            )
        ).all()
        before_count = len(before)

        before_companies = (
            await db_session.execute(
                select(CompanyModel).where(CompanyModel.company_slug == "boom-audit-co")
            )
        ).scalar_one_or_none()
        assert before_companies is None

        created_exc: Exception | None = None
        try:
            created = await api_client.post(
                "/api/v1/companies",
                json={
                    "company_name": "Boom Audit Co",
                    "company_slug": "boom-audit-co",
                    "email": "boom@audit-fail.co",
                    "timezone": "UTC",
                },
            )
        except RuntimeError as exc:
            created_exc = exc
            created = None  # type: ignore[assignment]
        if created is not None:
            assert created.status_code >= 400, created.text
        else:
            assert created_exc is not None
            assert "forced audit failure" in str(created_exc)

        db_session.expire_all()
        after_company = (
            await db_session.execute(
                select(CompanyModel).where(CompanyModel.company_slug == "boom-audit-co")
            )
        ).scalar_one_or_none()
        assert after_company is None

        after = (
            await db_session.execute(
                select(AuditLogModel.action).where(
                    AuditLogModel.action == "COMPANY_CREATED",
                )
            )
        ).all()
        assert len(after) == before_count
    finally:
        app.dependency_overrides.pop(get_audit_logger, None)
