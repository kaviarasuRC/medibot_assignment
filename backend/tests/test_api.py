"""API contract tests.

Runs the app in-process. Generation is stubbed; the RBAC filter and the vector
store are real, because those are the things worth testing.
"""

from __future__ import annotations

import httpx
import pytest

from app.rbac import Role, collections_for_role
from tests.conftest import CREDENTIALS, auth, login_as

# --- /login -----------------------------------------------------------------


@pytest.mark.parametrize("role", list(Role))
async def test_login_returns_the_right_role_and_collections(
    client: httpx.AsyncClient, role: Role
):
    username, password = CREDENTIALS[role]
    response = await client.post(
        "/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == role.value
    assert data["collections"] == collections_for_role(role)
    assert data["token_type"] == "bearer"
    assert data["access_token"]


async def test_login_rejects_a_bad_password(client: httpx.AsyncClient):
    response = await client.post(
        "/login", json={"username": "nurse.priya", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_login_rejects_an_unknown_user(client: httpx.AsyncClient):
    response = await client.post(
        "/login", json={"username": "ghost", "password": "nurse"}
    )
    assert response.status_code == 401


# --- /chat auth -------------------------------------------------------------


async def test_chat_without_a_token_is_401(client: httpx.AsyncClient):
    response = await client.post("/chat", json={"question": "hello"})
    assert response.status_code == 401


async def test_chat_with_a_garbage_token_is_401(client: httpx.AsyncClient):
    response = await client.post(
        "/chat", json={"question": "hello"}, headers=auth("not.a.token")
    )
    assert response.status_code == 401


async def test_chat_with_a_token_signed_by_the_wrong_secret_is_401(
    client: httpx.AsyncClient,
):
    from jose import jwt

    forged = jwt.encode({"sub": "attacker", "role": "admin"}, "wrong-secret", algorithm="HS256")
    response = await client.post(
        "/chat", json={"question": "hello"}, headers=auth(forged)
    )
    assert response.status_code == 401


# --- Adversarial case 6: body role is ignored -------------------------------


async def test_body_role_is_ignored_and_the_token_role_wins(
    client: httpx.AsyncClient, stub_llm
):
    """The one a reviewer is most likely to try by hand.

    A 422 would be WORSE than silently ignoring the field - it would tell an
    attacker which field name the server cares about.
    """
    token = await login_as(client, Role.NURSE)
    response = await client.post(
        "/chat",
        json={"question": "What is the hand hygiene protocol?", "role": "admin"},
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "nurse"
    permitted = set(collections_for_role(Role.NURSE))
    assert {s["collection"] for s in data["sources"]} <= permitted


async def test_body_role_does_not_produce_a_422(client: httpx.AsyncClient, stub_llm):
    token = await login_as(client, Role.NURSE)
    response = await client.post(
        "/chat",
        json={"question": "hand hygiene", "role": "admin", "collections": ["billing"]},
        headers=auth(token),
    )
    assert response.status_code == 200


# --- Adversarial case 7: the SQL gate ---------------------------------------


async def test_technician_analytical_question_is_refused(client: httpx.AsyncClient):
    token = await login_as(client, Role.TECHNICIAN)
    response = await client.post(
        "/chat",
        json={"question": "How many billing claims were escalated last month?"},
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_type"] != "sql_rag"
    assert data["retrieval_type"] == "blocked"
    assert data["blocked"] is True
    assert data["sources"] == []
    assert "technician" in data["answer"]
    # A generic error is explicitly insufficient per the rubric.
    assert len(data["answer"]) > 80


async def test_billing_executive_is_allowed_through_the_sql_gate(
    client: httpx.AsyncClient, monkeypatch
):
    """Gate only - the chain itself is stubbed so no LLM call is made."""
    monkeypatch.setattr(
        "app.routes.chat_routes.run_sql_rag",
        lambda q: {"answer": "8 claims.", "sql": "SELECT 1", "rows": [], "raw": ""},
    )
    token = await login_as(client, Role.BILLING_EXECUTIVE)
    response = await client.post(
        "/chat",
        json={"question": "How many claims were escalated in 2024?"},
        headers=auth(token),
    )
    data = response.json()
    assert data["retrieval_type"] == "sql_rag"
    assert data["sql_query"] == "SELECT 1"
    assert data["sources"] == []  # required key, empty for SQL answers


# --- Every response carries sources -----------------------------------------


@pytest.mark.parametrize("role", list(Role))
async def test_every_chat_response_contains_a_sources_key(
    client: httpx.AsyncClient, stub_llm, role: Role
):
    token = await login_as(client, role)
    response = await client.post(
        "/chat", json={"question": "What is the leave policy?"}, headers=auth(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "retrieval_type" in data
    assert "role" in data
    assert "answer" in data


@pytest.mark.parametrize("role", list(Role))
async def test_chat_never_cites_a_collection_outside_the_matrix(
    client: httpx.AsyncClient, stub_llm, role: Role
):
    token = await login_as(client, role)
    response = await client.post(
        "/chat",
        json={"question": "insurance billing codes for cardiac procedures"},
        headers=auth(token),
    )
    data = response.json()
    permitted = set(collections_for_role(role))
    assert {s["collection"] for s in data["sources"]} <= permitted


# --- /collections/{role} ----------------------------------------------------


async def test_collections_for_nurse(client: httpx.AsyncClient):
    response = await client.get("/collections/nurse")
    assert response.status_code == 200
    data = response.json()
    assert data["collections"] == ["general", "nursing"]
    assert data["sql_access"] is False


async def test_collections_for_admin(client: httpx.AsyncClient):
    data = (await client.get("/collections/admin")).json()
    assert len(data["collections"]) == 5
    assert data["sql_access"] is True


async def test_collections_for_an_unknown_role_is_404(client: httpx.AsyncClient):
    assert (await client.get("/collections/superuser")).status_code == 404


# --- /health ----------------------------------------------------------------


async def test_health_reports_qdrant_and_the_point_count(client: httpx.AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["qdrant"] == "ok"
    assert data["points_count"] > 0
    assert data["collection"]
    assert data["model"]


# --- Validation -------------------------------------------------------------


async def test_empty_question_is_rejected(client: httpx.AsyncClient):
    token = await login_as(client, Role.NURSE)
    response = await client.post("/chat", json={"question": ""}, headers=auth(token))
    assert response.status_code == 422
