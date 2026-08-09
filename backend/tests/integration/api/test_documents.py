"""Integration tests for Document Management API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.auth import UserModel
from app.infrastructure.database.models.company import CompanyModel
from app.infrastructure.database.seed_rbac import seed_rbac


@pytest.fixture
async def doc_seed(db_session: AsyncSession, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from app.core.config.settings import get_settings

    get_settings.cache_clear()

    roles = await seed_rbac(db_session)
    company_a = CompanyModel(
        company_name="Docs A",
        company_slug="docs-a",
        email="ops@docs-a.co",
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
        company_name="Docs B",
        company_slug="docs-b",
        email="ops@docs-b.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add_all([company_a, company_b])
    await db_session.flush()
    password = "Str0ng!Password"
    hashed = hash_password(password)
    admin_a = UserModel(
        company_id=company_a.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Ada",
        last_name="Admin",
        email="admin@docs-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    agent_a = UserModel(
        company_id=company_a.company_id,
        role_id=roles["SUPPORT_AGENT"],
        first_name="Eve",
        last_name="Agent",
        email="agent@docs-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    admin_b = UserModel(
        company_id=company_b.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Bea",
        last_name="Admin",
        email="admin@docs-b.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add_all([admin_a, agent_a, admin_b])
    await db_session.commit()
    return {
        "password": password,
        "company_a_id": int(company_a.company_id),
        "company_b_id": int(company_b.company_id),
        "emails": {
            "admin_a": "admin@docs-a.co",
            "agent_a": "agent@docs-a.co",
            "admin_b": "admin@docs-b.co",
        },
    }


async def _token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_documents_require_jwt(api_client: AsyncClient, doc_seed: dict) -> None:
    _ = doc_seed
    resp = await api_client.get("/api/v1/documents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_list_get_update_status_flow(
    api_client: AsyncClient,
    doc_seed: dict,
) -> None:
    token = await _token(api_client, doc_seed["emails"]["admin_a"], doc_seed["password"])
    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": ("policy.txt", b"Refund Policy content for indexing.", "text/plain")},
        data={"document_name": "Refund Policy", "tags": '["policy"]'},
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()["data"]
    assert body["document_name"] == "Refund Policy"
    assert body["processing_status"] == "QUEUED"
    assert body["company_id"] == doc_seed["company_a_id"]
    doc_id = body["document_id"]

    listed = await api_client.get("/api/v1/documents", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] == 1

    got = await api_client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["data"]["file_hash"]

    status_resp = await api_client.get(
        f"/api/v1/documents/{doc_id}/status",
        headers=_auth(token),
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["processing_status"] == "QUEUED"

    updated = await api_client.put(
        f"/api/v1/documents/{doc_id}",
        headers=_auth(token),
        json={"document_name": "Refund Policy v2", "description": "Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["document_name"] == "Refund Policy v2"

    storage = await api_client.get("/api/v1/documents/storage", headers=_auth(token))
    assert storage.status_code == 200
    assert storage.json()["data"]["document_count"] == 1

    reindex = await api_client.post(
        f"/api/v1/documents/{doc_id}/reindex",
        headers=_auth(token),
    )
    assert reindex.status_code == 200, reindex.text
    assert reindex.json()["data"]["processing_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_agent_cannot_upload_or_delete(api_client: AsyncClient, doc_seed: dict) -> None:
    admin_token = await _token(api_client, doc_seed["emails"]["admin_a"], doc_seed["password"])
    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(admin_token),
        files={"file": ("note.txt", b"hello agent", "text/plain")},
        data={"document_name": "Note"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    agent_token = await _token(api_client, doc_seed["emails"]["agent_a"], doc_seed["password"])
    denied = await api_client.post(
        "/api/v1/documents",
        headers=_auth(agent_token),
        files={"file": ("nope.txt", b"no", "text/plain")},
    )
    assert denied.status_code == 403

    readable = await api_client.get(f"/api/v1/documents/{doc_id}", headers=_auth(agent_token))
    assert readable.status_code == 200

    delete_denied = await api_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=_auth(agent_token),
    )
    assert delete_denied.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_and_soft_delete_restore(
    api_client: AsyncClient,
    doc_seed: dict,
) -> None:
    token_a = await _token(api_client, doc_seed["emails"]["admin_a"], doc_seed["password"])
    token_b = await _token(api_client, doc_seed["emails"]["admin_b"], doc_seed["password"])

    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(token_a),
        files={"file": ("shared-name.pdf", b"tenant-a-bytes", "application/pdf")},
        data={"document_name": "A Only"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    denied = await api_client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token_b))
    assert denied.status_code == 403

    deleted = await api_client.delete(f"/api/v1/documents/{doc_id}", headers=_auth(token_a))
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None

    missing = await api_client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token_a))
    assert missing.status_code == 404

    listed = await api_client.get("/api/v1/documents", headers=_auth(token_a))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] == 0

    restored = await api_client.post(
        f"/api/v1/documents/{doc_id}/restore",
        headers=_auth(token_a),
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["deleted_at"] is None
