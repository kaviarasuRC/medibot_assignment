"""POST /chat - the main RAG endpoint.

The role comes from `get_current_role()` and from nowhere else. A `role` field
in the request body is discarded by `ChatRequest`'s `extra="ignore"` before this
function ever sees it. Accepting a body role "for convenience" would make this a
UI-level control and lose the whole access-control argument.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_role
from app.generate import GenerationUnavailable
from app.models import ChatRequest, ChatResponse
from app.rag_pipeline import answer_document_question
from app.rbac import RBACViolation, Role, can_use_sql_rag, sql_refusal_message
from app.router import RetrievalRoute, explain, route
from app.sql_rag import SQLRagError, UnsafeSQL, run_sql_rag

log = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    role: Role = Depends(get_current_role),
) -> ChatResponse:
    question = payload.question.strip()
    decision = route(question)
    log.info("chat role=%s route=%s %s", role.value, decision.value, explain(question))

    try:
        if decision is RetrievalRoute.SQL_RAG:
            return _answer_analytical(question, role)
        return answer_document_question(question, role)

    except RBACViolation:
        # Layer 3 fired: the query filter let something through. Never answer.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An access-control check failed. The request was not answered.",
        )
    except GenerationUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


def _answer_analytical(question: str, role: Role) -> ChatResponse:
    """The SQL branch, gated by role BEFORE any query is generated or run."""
    if not can_use_sql_rag(role):
        # Routing is evaluated before this check, so a technician asking an
        # analytical question gets the specific "SQL analytics isn't available
        # to your role" message rather than a confusing document-search miss.
        #
        # retrieval_type is "blocked", not "sql_rag": NEITHER pipeline ran, so
        # labelling it sql_rag would be a lie in the API contract and would make
        # adversarial case 7 untestable by assertion.
        log.info("SQL RAG refused for role=%s", role.value)
        return ChatResponse(
            answer=sql_refusal_message(role),
            sources=[],
            retrieval_type="blocked",
            role=role.value,
            blocked=True,
        )

    try:
        result = run_sql_rag(question)
    except (UnsafeSQL, SQLRagError) as exc:
        log.warning("SQL RAG failed for %r: %s", question, exc)
        return ChatResponse(
            answer=(
                "I couldn't turn that into a safe database query. Try rephrasing it "
                f"as a question about claims or maintenance tickets. ({exc})"
            ),
            sources=[],
            retrieval_type="sql_rag",
            role=role.value,
        )

    return ChatResponse(
        answer=str(result["answer"]),
        # `sources` is required in EVERY response per the rubric. For a SQL
        # answer it is [] with sql_query populated.
        sources=[],
        retrieval_type="sql_rag",
        role=role.value,
        sql_query=str(result["sql"]),
    )
