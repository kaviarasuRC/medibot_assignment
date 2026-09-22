"""The Qdrant client, collection schema, and payload indexes.

Shared by ingestion (which writes) and retrieval (which reads), so the schema is
defined exactly once.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.config import settings

log = logging.getLogger(__name__)

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "bm25"

# Both fields the system filters on. The RBAC filter sits on the hot path twice
# (once per hybrid branch), so these are not optional for performance.
INDEXED_PAYLOAD_FIELDS = ("access_roles", "collection", "source_document")


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    log.info("Connecting to Qdrant at %s", settings.qdrant_url)
    return QdrantClient(url=settings.qdrant_url, timeout=60)


def collection_exists() -> bool:
    return get_client().collection_exists(settings.qdrant_collection)


def ensure_collection(recreate: bool = False) -> None:
    """Create the collection with both vector types, plus payload indexes."""
    client = get_client()
    name = settings.qdrant_collection

    if recreate and client.collection_exists(name):
        log.warning("Dropping existing collection %s", name)
        client.delete_collection(name)

    if not client.collection_exists(name):
        log.info("Creating collection %s", name)
        client.create_collection(
            collection_name=name,
            vectors_config={
                DENSE_VECTOR: models.VectorParams(
                    size=settings.embed_dim,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                # Modifier.IDF is REQUIRED, not optional. FastEmbed's
                # `Qdrant/bm25` emits only the term-frequency half of the BM25
                # score; the IDF component depends on corpus statistics and
                # cannot be precomputed per-document. Setting the modifier makes
                # Qdrant compute IDF server-side from live collection
                # statistics. Omit it and common words dominate the ranking -
                # you get a BM25-shaped thing that is not BM25, and it still
                # returns results, which is exactly why it is dangerous.
                SPARSE_VECTOR: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                ),
            },
        )

    for field in INDEXED_PAYLOAD_FIELDS:
        # KEYWORD is correct for a list-of-strings: Qdrant indexes each array
        # element and has no separate array type.
        client.create_payload_index(
            collection_name=name,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )
    log.info("Payload indexes ensured on: %s", ", ".join(INDEXED_PAYLOAD_FIELDS))


def delete_document(source_document: str) -> None:
    """Remove every point belonging to one source document.

    Deterministic point IDs alone are NOT sufficient for idempotent re-ingestion.
    If a document is edited and gets shorter, the high-index chunks from the
    previous run are never overwritten - they stay live and retrievable,
    answering questions with stale text, and the point count won't tell you.
    So each document is deleted by filter before it is re-ingested.
    """
    get_client().delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="source_document",
                        match=models.MatchValue(value=source_document),
                    )
                ]
            )
        ),
        wait=True,
    )


def count_points() -> int:
    return get_client().count(
        collection_name=settings.qdrant_collection, exact=True
    ).count
