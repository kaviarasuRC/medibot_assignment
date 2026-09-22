"""Hybrid retrieval: dense + BM25 in one query, fused server-side, RBAC pre-filtered.

The assignment requires that both searches be "queried together at retrieval
time - not run as two separate queries and merged in application code". Fusion
happens inside Qdrant, in a single `query_points` call.

The access-control property that makes this design correct: `query_filter` is
passed at the TOP level, not inside each `Prefetch`. Qdrant propagates the
filter of each level down into the leaves of the prefetch tree, so each branch's
`limit` is applied to already-filtered candidates. One place, both branches,
pre-filter.
"""

from __future__ import annotations

import logging

from qdrant_client import models
from qdrant_client.models import ScoredPoint

from app.config import settings
from app.embeddings import embed_query, embed_query_sparse
from app.rbac import Role, rbac_filter
from app.vector_store import DENSE_VECTOR, SPARSE_VECTOR, get_client

log = logging.getLogger(__name__)


def hybrid_search(
    question: str,
    role: Role | str,
    limit: int | None = None,
) -> list[ScoredPoint]:
    """Dense + BM25, RRF-fused, scoped to what `role` may read.

    Raises `PermissionDenied` (via `rbac_filter`) for an unknown role, rather
    than returning an unfiltered result set.
    """
    limit = limit or settings.retrieval_top_k

    q_dense = embed_query(question)
    q_sparse = embed_query_sparse(question)

    result = get_client().query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            models.Prefetch(query=q_dense, using=DENSE_VECTOR, limit=limit),
            models.Prefetch(query=q_sparse, using=SPARSE_VECTOR, limit=limit),
        ],
        # RRF over DBSF: DBSF normalizes each branch's raw scores by their
        # distribution before summing, which is tempting because it uses score
        # magnitude - but it is computed per shard, so its scores vary with
        # shard_number. For an access-control-sensitive system, rank-based RRF
        # is the stabler default.
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=rbac_filter(role),  # <- propagates into BOTH branches
        limit=limit,
        with_payload=True,
    )

    log.debug(
        "hybrid_search role=%s limit=%d -> %d points",
        getattr(role, "value", role),
        limit,
        len(result.points),
    )
    return result.points


def dense_search(
    question: str,
    role: Role | str,
    limit: int | None = None,
) -> list[ScoredPoint]:
    """Dense-only retrieval. Used ONLY by the comparison harness.

    Carries the identical RBAC filter, so the comparison measures retrieval
    quality and nothing else.
    """
    limit = limit or settings.retrieval_top_k
    return get_client().query_points(
        collection_name=settings.qdrant_collection,
        query=embed_query(question),
        using=DENSE_VECTOR,
        query_filter=rbac_filter(role),
        limit=limit,
        with_payload=True,
    ).points


def sparse_search(
    question: str,
    role: Role | str,
    limit: int | None = None,
) -> list[ScoredPoint]:
    """BM25-only retrieval. Used ONLY by the comparison harness."""
    limit = limit or settings.retrieval_top_k
    return get_client().query_points(
        collection_name=settings.qdrant_collection,
        query=embed_query_sparse(question),
        using=SPARSE_VECTOR,
        query_filter=rbac_filter(role),
        limit=limit,
        with_payload=True,
    ).points
