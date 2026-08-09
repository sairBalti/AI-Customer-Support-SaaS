"""Integration/API tests for Knowledge Base processing and search."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.core.security.password import hash_password
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.auth import UserModel
from app.infrastructure.database.models.company import CompanyModel
from app.infrastructure.database.seed_rbac import seed_rbac


@pytest.fixture
async def knowledge_seed(db_session: AsyncSession, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hashing")
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "chroma")
    get_settings.cache_clear()

    roles = await seed_rbac(db_session)
    company_a = CompanyModel(
        company_name="Know A",
        company_slug="know-a",
        email="ops@know-a.co",
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
        company_name="Know B",
        company_slug="know-b",
        email="ops@know-b.co",
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
        email="admin@know-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    agent_a = UserModel(
        company_id=company_a.company_id,
        role_id=roles["SUPPORT_AGENT"],
        first_name="Eve",
        last_name="Agent",
        email="agent@know-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    admin_b = UserModel(
        company_id=company_b.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Bea",
        last_name="Admin",
        email="admin@know-b.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    customer = UserModel(
        company_id=company_a.company_id,
        role_id=roles["CUSTOMER"],
        first_name="Cal",
        last_name="Customer",
        email="customer@know-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add_all([admin_a, agent_a, admin_b, customer])
    await db_session.commit()
    return {
        "password": password,
        "company_a_id": int(company_a.company_id),
        "emails": {
            "admin_a": "admin@know-a.co",
            "agent_a": "agent@know-a.co",
            "admin_b": "admin@know-b.co",
            "customer": "customer@know-a.co",
        },
    }


async def _token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_process_search_isolation_and_delete(
    api_client: AsyncClient,
    knowledge_seed: dict,
) -> None:
    token_a = await _token(
        api_client, knowledge_seed["emails"]["admin_a"], knowledge_seed["password"]
    )
    token_b = await _token(
        api_client, knowledge_seed["emails"]["admin_b"], knowledge_seed["password"]
    )

    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(token_a),
        files={
            "file": (
                "refund.txt",
                b"Company A refund policy allows returns within thirty days.",
                "text/plain",
            )
        },
        data={"document_name": "Refund"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    processed = await api_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=_auth(token_a),
    )
    assert processed.status_code == 200, processed.text
    assert processed.json()["data"]["processing_status"] == "COMPLETED"
    assert processed.json()["data"]["total_chunks"] >= 1

    search_a = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(token_a),
        json={"query": "refund returns", "top_k": 5},
    )
    assert search_a.status_code == 200, search_a.text
    items_a = search_a.json()["data"]["items"]
    assert items_a
    assert all(i["document_id"] == doc_id for i in items_a)

    search_b = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(token_b),
        json={"query": "refund returns", "top_k": 5},
    )
    assert search_b.status_code == 200, search_b.text
    assert search_b.json()["data"]["items"] == []

    cross = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(token_b),
        json={"query": "refund", "document_id": doc_id},
    )
    assert cross.status_code == 403

    deleted = await api_client.delete(f"/api/v1/documents/{doc_id}", headers=_auth(token_a))
    assert deleted.status_code == 200
    search_after = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(token_a),
        json={"query": "refund returns", "top_k": 5},
    )
    assert search_after.status_code == 200
    assert search_after.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_rbac_process_and_search(api_client: AsyncClient, knowledge_seed: dict) -> None:
    admin = await _token(
        api_client, knowledge_seed["emails"]["admin_a"], knowledge_seed["password"]
    )
    agent = await _token(
        api_client, knowledge_seed["emails"]["agent_a"], knowledge_seed["password"]
    )
    customer = await _token(
        api_client, knowledge_seed["emails"]["customer"], knowledge_seed["password"]
    )

    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(admin),
        files={
            "file": ("note.txt", b"support agent searchable content about shipping", "text/plain")
        },
        data={"document_name": "Note"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["data"]["document_id"]

    denied_agent_process = await api_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=_auth(agent),
    )
    assert denied_agent_process.status_code == 403

    denied_customer = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(customer),
        json={"query": "shipping"},
    )
    assert denied_customer.status_code == 403

    processed = await api_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=_auth(admin),
    )
    assert processed.status_code == 200, processed.text

    agent_search = await api_client.post(
        "/api/v1/knowledge/search",
        headers=_auth(agent),
        json={"query": "shipping"},
    )
    assert agent_search.status_code == 200, agent_search.text
    assert agent_search.json()["data"]["items"]

    reindex = await api_client.post(
        f"/api/v1/documents/{doc_id}/reindex",
        headers=_auth(admin),
    )
    assert reindex.status_code == 200, reindex.text
    assert reindex.json()["data"]["processing_status"] == "COMPLETED"
