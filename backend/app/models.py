"""Pydantic request/response schemas - the API contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RetrievalType = Literal["hybrid_rag", "sql_rag", "blocked"]


# --- Auth -------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    collections: list[str]
    sql_access: bool


# --- Chat -------------------------------------------------------------------


class ChatRequest(BaseModel):
    # `extra="ignore"` rather than `extra="forbid"` is deliberate. A client that
    # sends {"question": "...", "role": "admin"} should be SILENTLY DOWNGRADED
    # to its real token role, not handed a 422 that tells an attacker which
    # field name the server cares about. This is adversarial test case 6.
    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=1, max_length=2000)
    # NOTE: there is deliberately no `role` field. The role comes from the
    # bearer token via get_current_role(), and from nowhere else.


class Source(BaseModel):
    source_document: str
    section_title: str
    collection: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieval_type: RetrievalType
    role: str

    # Beyond the spec, useful for the demo and for asserting in tests.
    rerank_scores: list[float] | None = None
    sql_query: str | None = None
    blocked: bool = False


# --- Meta -------------------------------------------------------------------


class CollectionsResponse(BaseModel):
    role: str
    collections: list[str]
    sql_access: bool


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    groq: str
    collection: str
    points_count: int
    model: str
