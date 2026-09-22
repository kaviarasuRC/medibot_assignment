"""Shared fixtures.

The API tests run the app in-process over an ASGI transport - no server, no
port. The LLM is stubbed so the suite is hermetic and fast; what is under test
is the role plumbing and the API contract, not Groq.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

from app.chunk import Chunk
from app.models import Source
from app.rbac import Role


@pytest.fixture
def stub_llm(monkeypatch):
    """Replace generation with a deterministic stub.

    Patched where it is *used* (`app.rag_pipeline`), not where it is defined -
    `rag_pipeline` imported the name at module load, so patching
    `app.generate.generate_answer` would have no effect.
    """

    def fake_generate_answer(
        question: str, role, chunks: list[tuple[float, Chunk]]
    ) -> tuple[str, list[Source]]:
        from app.generate import build_sources
        from app.rbac import refusal_message

        if not chunks:
            return refusal_message(role), []
        return (
            f"[stubbed answer for role={getattr(role, 'value', role)}]",
            build_sources(chunks),
        )

    monkeypatch.setattr("app.rag_pipeline.generate_answer", fake_generate_answer)
    return fake_generate_answer


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", timeout=120
    ) as c:
        yield c


CREDENTIALS: dict[Role, tuple[str, str]] = {
    Role.DOCTOR: ("dr.mehta", "doctor"),
    Role.NURSE: ("nurse.priya", "nurse"),
    Role.BILLING_EXECUTIVE: ("billing.ravi", "billing"),
    Role.TECHNICIAN: ("tech.anand", "technician"),
    Role.ADMIN: ("admin.sys", "admin"),
}


async def login_as(client: httpx.AsyncClient, role: Role) -> str:
    username, password = CREDENTIALS[role]
    response = await client.post(
        "/login", json={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
