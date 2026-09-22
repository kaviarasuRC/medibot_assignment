"""Document-question orchestration: retrieve -> assert -> rerank -> generate.

The layer-3 assertion lives here. It is worth its handful of lines because it
converts a silent leak into a loud crash during development, and it is trivially
demonstrable to a reviewer.
"""

from __future__ import annotations

import logging

from qdrant_client.models import ScoredPoint

from app.chunk import Chunk
from app.config import settings
from app.generate import generate_answer
from app.models import ChatResponse
from app.rbac import (
    ROLE_COLLECTIONS,
    RBACViolation,
    Role,
    coerce_role,
    refusal_message,
)
from app.rerank import rerank
from app.retrieval import hybrid_search

log = logging.getLogger(__name__)


def assert_in_policy(points: list[ScoredPoint], role: Role) -> None:
    """Layer 3: re-check every returned chunk against the matrix.

    The query filter is the real enforcement. This exists so that a regression
    in filter construction becomes loud rather than silent. On violation it logs
    CRITICAL and raises - it never answers the question with a reduced set,
    because a pipeline that quietly drops leaked chunks is a pipeline whose leak
    nobody ever notices.
    """
    allowed = {c.value for c in ROLE_COLLECTIONS[role]}
    for point in points:
        collection = (point.payload or {}).get("collection")
        if collection not in allowed:
            log.critical(
                "RBAC LEAK role=%s collection=%s point=%s source=%s",
                role.value,
                collection,
                point.id,
                (point.payload or {}).get("source_document"),
            )
            raise RBACViolation(
                f"Retrieved a {collection!r} chunk for role {role.value!r}; "
                f"permitted collections are {sorted(allowed)}"
            )


def answer_document_question(question: str, role: Role | str) -> ChatResponse:
    """The hybrid RAG path."""
    resolved = coerce_role(role)

    points = hybrid_search(question, resolved, limit=settings.retrieval_top_k)
    assert_in_policy(points, resolved)

    candidates = [
        Chunk.from_point(point, hybrid_rank=rank)
        for rank, point in enumerate(points, start=1)
    ]
    reranked = rerank(question, candidates, top_k=settings.rerank_top_k)

    # Apply the relevance floor. Retrieval always returns *something* - the
    # question is whether any of it is actually on topic. A technician asking
    # about amiodarone will match general-collection text weakly; answering
    # from it would be worse than refusing.
    relevant = [pair for pair in reranked if pair[0] >= settings.rerank_min_score]
    if reranked and not relevant:
        log.info(
            "Best rerank score %.4f is below the floor %.2f for role=%s; refusing",
            reranked[0][0],
            settings.rerank_min_score,
            resolved.value,
        )
    reranked = relevant

    if not reranked:
        # Nothing the user may see is relevant. Return the role-scoped refusal
        # without calling the LLM.
        log.info("No in-policy chunks for role=%s; refusing", resolved.value)
        return ChatResponse(
            answer=refusal_message(resolved),
            sources=[],
            retrieval_type="blocked",
            role=resolved.value,
            blocked=True,
        )

    answer, sources = generate_answer(question, resolved, reranked)

    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieval_type="hybrid_rag",
        role=resolved.value,
        rerank_scores=[round(score, 4) for score, _ in reranked],
    )
