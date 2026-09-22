"""Offline ingestion: PDF/Markdown -> retrievable, access-labelled chunks.

    uv run python -m ingest.ingest --recreate

Run once before anything else works. Per document:

  0. delete any existing points for this source_document  (orphan removal)
  1. parse with Docling                                   (structure preserved)
  2. chunk hierarchically, then token-aware               (HybridChunker)
  3. embed contextualize(chunk); store and cite chunk.text
  4. upsert both vectors on one point, plus access metadata
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path

from qdrant_client import models

from app.config import settings
from app.embeddings import (
    batched,
    embed_documents,
    embed_documents_sparse,
    warm,
)
from app.rbac import roles_for_collection
from app.vector_store import (
    DENSE_VECTOR,
    SPARSE_VECTOR,
    count_points,
    delete_document,
    ensure_collection,
    get_client,
)
from ingest.chunking import (
    chunk_type,
    contextualize,
    get_chunker,
    section_title,
    source_document,
)
from ingest.collection_map import collection_for_path, discover_documents
from ingest.parse import to_docling_document

log = logging.getLogger("ingest")

UPSERT_BATCH = 64

# Stable namespace so point IDs are reproducible across runs and machines.
NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def point_id(source: str, index: int) -> str:
    """Deterministic, so a re-run updates in place instead of duplicating."""
    return str(uuid.uuid5(NAMESPACE, f"{source}:{index}"))


def ingest_document(path: Path) -> int:
    """Ingest one file. Returns the number of points written."""
    collection = collection_for_path(path)
    access_roles = roles_for_collection(collection)  # derived, never hand-written

    doc = to_docling_document(path)
    chunks = list(get_chunker().chunk(dl_doc=doc))
    if not chunks:
        log.warning("%s produced no chunks - skipping", path.name)
        return 0

    embed_texts = [contextualize(c) for c in chunks]  # heading chain + body
    dense_vectors = embed_documents(embed_texts)
    sparse_vectors = embed_documents_sparse(embed_texts)

    points: list[models.PointStruct] = []
    for index, chunk in enumerate(chunks):
        src = source_document(chunk, fallback_name=path.name)
        points.append(
            models.PointStruct(
                id=point_id(src, index),
                vector={
                    DENSE_VECTOR: dense_vectors[index],
                    SPARSE_VECTOR: sparse_vectors[index],
                },
                payload={
                    "source_document": src,
                    "collection": collection.value,
                    "access_roles": access_roles,
                    "section_title": section_title(chunk),
                    "chunk_type": chunk_type(chunk),
                    "text": chunk.text,  # raw text, for citation display
                    "chunk_index": index,
                },
            )
        )

    # Step 0 - remove the previous run's points for this document BEFORE
    # writing. Deterministic IDs overwrite but never delete, so a document that
    # has become shorter would otherwise leave orphan chunks live.
    source_names = {p.payload["source_document"] for p in points}
    for name in source_names:
        delete_document(name)

    client = get_client()
    for batch in batched(points, UPSERT_BATCH):
        client.upsert(
            collection_name=settings.qdrant_collection, points=batch, wait=True
        )

    types = sorted({p.payload["chunk_type"] for p in points})
    log.info(
        "  %-32s -> %3d chunks  collection=%-9s roles=%s  types=%s",
        path.name,
        len(points),
        collection.value,
        ",".join(access_roles),
        ",".join(types),
    )
    return len(points)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and rebuild the collection before ingesting.",
    )
    parser.add_argument(
        "--only",
        metavar="SUBSTRING",
        help="Ingest only files whose path contains SUBSTRING (for re-running one file).",
    )
    args = parser.parse_args(argv)

    # The corpus contains characters outside the Windows console codepage
    # (the rupee sign, in the billing documents). Without this, logging a
    # chunk preview raises UnicodeEncodeError.
    from app.console import setup as console_setup

    console_setup()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # Docling is extremely chatty at INFO.
    for noisy in ("docling", "docling_core", "transformers", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    documents = discover_documents(settings.documents_abspath)
    if args.only:
        documents = [p for p in documents if args.only in str(p)]
        if not documents:
            log.error("No documents matched --only %r", args.only)
            return 1

    log.info("Ingesting %d document(s) from %s", len(documents), settings.documents_abspath)
    ensure_collection(recreate=args.recreate)
    warm()
    get_chunker()  # asserts the token limit actually took effect

    total = 0
    for path in documents:
        total += ingest_document(path)

    log.info("Done. %d chunks written; collection now holds %d points.", total, count_points())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
