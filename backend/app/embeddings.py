"""FastEmbed singletons for the dense and sparse vectors.

Both models are loaded once and reused. Instantiating them per request would add
seconds of latency to every call.

Document vs query asymmetry matters here and is not cosmetic:

- `embed()` is for documents.
- `query_embed()` is for queries. For BM25 it skips document-length
  normalization and emits flat term weights, which is the correct asymmetry.

FastEmbed returns numpy arrays. `.tolist()` is required, or pydantic validation
on `models.SparseVector` fails.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import models

from app.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def dense_model() -> TextEmbedding:
    log.info("Loading dense embedding model: %s", settings.embed_model)
    return TextEmbedding(settings.embed_model)


@lru_cache(maxsize=1)
def sparse_model() -> SparseTextEmbedding:
    log.info("Loading sparse embedding model: %s", settings.sparse_model)
    return SparseTextEmbedding(settings.sparse_model)


def warm() -> None:
    """Force both models to load. Called at API startup and before ingestion."""
    dense_model()
    sparse_model()


# --- Document side ----------------------------------------------------------


def embed_documents(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in dense_model().embed(texts)]


def embed_documents_sparse(texts: list[str]) -> list[models.SparseVector]:
    return [_to_sparse_vector(e) for e in sparse_model().embed(texts)]


# --- Query side -------------------------------------------------------------


def embed_query(text: str) -> list[float]:
    return next(iter(dense_model().query_embed(text))).tolist()


def embed_query_sparse(text: str) -> models.SparseVector:
    return _to_sparse_vector(next(iter(sparse_model().query_embed(text))))


def _to_sparse_vector(embedding) -> models.SparseVector:
    return models.SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )


def batched(items: list, size: int) -> Iterable[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
