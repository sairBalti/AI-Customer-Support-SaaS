"""Integration tests for AI Customer Support Agent chat/RAG."""

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
async def chat_seed(db_session: AsyncSession, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hashing")
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "chroma")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    get_settings.cache_clear()

    roles = await seed_rbac(db_session)
    company_a = CompanyModel(
        company_name="Chat A",
        company_slug="chat-a",
        email="ops@chat-a.co",
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
        company_name="Chat B",
        company_slug="chat-b",
        email="ops@chat-b.co",
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
    customers = []
    for company, email, first in (
        (company_a, "cust@chat-a.co", "Ann"),
        (company_b, "cust@chat-b.co", "Ben"),
    ):
        user = UserModel(
            company_id=company.company_id,
            role_id=roles["CUSTOMER"],
            first_name=first,
            last_name="Customer",
            email=email,
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        )
        customers.append(user)
    agent = UserModel(
        company_id=company_a.company_id,
        role_id=roles["SUPPORT_AGENT"],
        first_name="Eve",
        last_name="Agent",
        email="agent@chat-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    admin = UserModel(
        company_id=company_a.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Ada",
        last_name="Admin",
        email="admin@chat-a.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add_all([*customers, agent, admin])
    await db_session.commit()
    return {
        "password": password,
        "emails": {
            "customer_a": "cust@chat-a.co",
            "customer_b": "cust@chat-b.co",
            "agent": "agent@chat-a.co",
            "admin": "admin@chat-a.co",
        },
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _token(api_client: AsyncClient, email: str, password: str) -> str:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["tokens"]["access_token"]


async def _index_policy(api_client: AsyncClient, admin_token: str) -> int:
    upload = await api_client.post(
        "/api/v1/documents",
        headers=_auth(admin_token),
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
        headers=_auth(admin_token),
    )
    assert processed.status_code == 200, processed.text
    assert processed.json()["data"]["processing_status"] == "COMPLETED"
    return int(doc_id)


@pytest.mark.asyncio
async def test_chat_rag_sources_and_isolation(
    api_client: AsyncClient,
    chat_seed: dict,
) -> None:
    admin = await _token(api_client, chat_seed["emails"]["admin"], chat_seed["password"])
    cust_a = await _token(api_client, chat_seed["emails"]["customer_a"], chat_seed["password"])
    cust_b = await _token(api_client, chat_seed["emails"]["customer_b"], chat_seed["password"])
    doc_id = await _index_policy(api_client, admin)

    created = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust_a),
        json={"title": "Refund help"},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["data"]["conversation_id"]

    answered = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=_auth(cust_a),
        json={"content": "What is your refund policy?"},
    )
    assert answered.status_code == 200, answered.text
    body = answered.json()["data"]
    assert body["used_knowledge"] is True
    assert body["answer"]
    assert body["sources"]
    assert body["sources"][0]["document_id"] == doc_id

    listed = await api_client.get(
        "/api/v1/chat/conversations",
        headers=_auth(cust_a),
    )
    assert listed.status_code == 200
    assert any(i["conversation_id"] == conversation_id for i in listed.json()["data"]["items"])

    detail = await api_client.get(
        f"/api/v1/chat/conversations/{conversation_id}",
        headers=_auth(cust_a),
    )
    assert detail.status_code == 200
    assert len(detail.json()["data"]["messages"]) >= 2

    denied = await api_client.get(
        f"/api/v1/chat/conversations/{conversation_id}",
        headers=_auth(cust_b),
    )
    assert denied.status_code == 403

    listed_b = await api_client.get(
        "/api/v1/chat/conversations",
        headers=_auth(cust_b),
    )
    assert listed_b.status_code == 200
    assert listed_b.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_chat_no_context_fallback_and_rbac(
    api_client: AsyncClient,
    chat_seed: dict,
) -> None:
    cust = await _token(api_client, chat_seed["emails"]["customer_a"], chat_seed["password"])
    agent = await _token(api_client, chat_seed["emails"]["agent"], chat_seed["password"])

    denied_agent = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(agent),
        json={},
    )
    assert denied_agent.status_code == 403

    created = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["data"]["conversation_id"]

    answered = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=_auth(cust),
        json={"content": "Do you ship to Mars?"},
    )
    assert answered.status_code == 200, answered.text
    data = answered.json()["data"]
    assert data["used_knowledge"] is False
    assert data["sources"] == []
    assert "knowledge base" in data["answer"].lower()


@pytest.mark.asyncio
async def test_delete_conversation_and_delete_all(
    api_client: AsyncClient,
    chat_seed: dict,
) -> None:
    cust = await _token(api_client, chat_seed["emails"]["customer_a"], chat_seed["password"])
    agent = await _token(api_client, chat_seed["emails"]["agent"], chat_seed["password"])

    first = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "One"},
    )
    second = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "Two"},
    )
    assert first.status_code == 201 and second.status_code == 201
    first_id = first.json()["data"]["conversation_id"]
    second_id = second.json()["data"]["conversation_id"]

    denied = await api_client.delete(
        f"/api/v1/chat/conversations/{first_id}",
        headers=_auth(agent),
    )
    assert denied.status_code == 403

    deleted = await api_client.delete(
        f"/api/v1/chat/conversations/{first_id}",
        headers=_auth(cust),
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"]["deleted"] is True

    missing = await api_client.get(
        f"/api/v1/chat/conversations/{first_id}",
        headers=_auth(cust),
    )
    assert missing.status_code == 404

    # Create another with messages so delete-all clears parent_message_id links too.
    third = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "Three"},
    )
    third_id = third.json()["data"]["conversation_id"]
    await api_client.post(
        f"/api/v1/chat/conversations/{third_id}/messages",
        headers=_auth(cust),
        json={"content": "hello"},
    )

    delete_all = await api_client.delete(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
    )
    assert delete_all.status_code == 200, delete_all.text
    assert delete_all.json()["data"]["deleted_count"] == 2

    listed = await api_client.get("/api/v1/chat/conversations", headers=_auth(cust))
    assert listed.status_code == 200
    assert listed.json()["data"]["items"] == []
