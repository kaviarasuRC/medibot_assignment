"""Print a sample of indexed chunks so the ingestion output can be read by eye.

    uv run python scripts/inspect_chunks.py [--n 5] [--collection billing]

`IMPLEMENTATION_PLAN.md` §2.5 is explicit that this output gets read, not
skimmed. Three things to check:

  - Does the embedded text actually START with the heading chain?
    (proves contextualize() worked)
  - Do table chunks look like coherent tables rather than fragments?
  - Does a `billing` chunk read access_roles ["admin", "billing_executive"]
    and nothing else?
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

# Running a script BY PATH puts the script's own directory on sys.path, not the
# working directory - so `backend/` has to be added explicitly for `app` and
# `ingest` to import. Keeps `uv run python scripts/<name>.py` working as
# documented, without making scripts/ a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.console import setup as _console_setup  # noqa: E402

_console_setup()

from app.config import settings  # noqa: E402
from app.rbac import Collection, roles_for_collection
from app.vector_store import count_points, get_client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5, help="How many chunks to print.")
    parser.add_argument("--collection", help="Only sample this collection.")
    parser.add_argument("--chunk-type", help="Only sample this chunk_type.")
    parser.add_argument("--chars", type=int, default=320, help="Preview length.")
    args = parser.parse_args(argv)

    client = get_client()
    if not client.collection_exists(settings.qdrant_collection):
        print(f"Collection {settings.qdrant_collection!r} does not exist. Run ingestion first.")
        return 1

    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        limit=10_000,
        with_payload=True,
        with_vectors=False,
    )
    if not points:
        print("Collection is empty. Run ingestion first.")
        return 1

    # --- Corpus summary -----------------------------------------------------
    print("=" * 78)
    print(f"COLLECTION {settings.qdrant_collection!r} - {count_points()} points")
    print("=" * 78)

    by_collection = Counter(p.payload["collection"] for p in points)
    by_type = Counter(p.payload["chunk_type"] for p in points)
    by_source = Counter(p.payload["source_document"] for p in points)

    print("\nchunks per collection")
    for name, n in sorted(by_collection.items()):
        print(f"  {name:<12} {n:>4}")
    print("\nchunks per chunk_type")
    for name, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<12} {n:>4}")
    print("\nchunks per source_document")
    for name, n in sorted(by_source.items()):
        print(f"  {name:<34} {n:>4}")

    # --- access_roles integrity --------------------------------------------
    print("\naccess_roles labels vs the matrix")
    ok = True
    for collection in Collection:
        expected = roles_for_collection(collection)
        seen = {
            tuple(sorted(p.payload["access_roles"]))
            for p in points
            if p.payload["collection"] == collection.value
        }
        if not seen:
            print(f"  {collection.value:<12} (no chunks)")
            continue
        for labels in seen:
            match = list(labels) == expected
            ok = ok and match
            flag = "OK  " if match else "WRONG"
            print(f"  {collection.value:<12} {flag} {list(labels)}")
    print(f"\n  => {'all labels match the matrix' if ok else 'MISMATCH - ingestion and rbac.py disagree'}")

    # --- Missing metadata ---------------------------------------------------
    required = ("source_document", "collection", "access_roles", "section_title", "chunk_type", "text")
    missing = [
        (p.payload.get("source_document"), field)
        for p in points
        for field in required
        if field not in p.payload
    ]
    empty_titles = sum(1 for p in points if not p.payload.get("section_title"))
    print(f"\nmetadata completeness")
    print(f"  missing required fields : {len(missing)}")
    print(f"  empty section_title     : {empty_titles} / {len(points)}")

    # --- Samples ------------------------------------------------------------
    pool = points
    if args.collection:
        pool = [p for p in pool if p.payload["collection"] == args.collection]
    if args.chunk_type:
        pool = [p for p in pool if p.payload["chunk_type"] == args.chunk_type]
    if not pool:
        print("\nNo chunks matched the filters.")
        return 1

    random.seed(7)  # reproducible samples
    for p in random.sample(pool, min(args.n, len(pool))):
        pay = p.payload
        print("\n" + "-" * 78)
        print(f"source_document : {pay['source_document']}")
        print(f"collection      : {pay['collection']}")
        print(f"access_roles    : {pay['access_roles']}")
        print(f"section_title   : {pay['section_title'] or '(none)'}")
        print(f"chunk_type      : {pay['chunk_type']}")
        text = pay["text"]
        preview = text[: args.chars].replace("\n", "\n                  ")
        print(f"text            : {preview}{'...' if len(text) > args.chars else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
