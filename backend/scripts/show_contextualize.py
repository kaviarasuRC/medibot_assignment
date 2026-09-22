"""Show what contextualize() actually produces - before and after.

    uv run python scripts/show_contextualize.py [--doc icu_nursing_procedures.pdf]

This is the proof for the 20% chunking criterion: each chunk's EMBEDDED text
carries its parent heading chain, while the stored/cited text stays the raw
paragraph. The payload only holds the raw text, so this cannot be shown from
the index - it has to be demonstrated at the chunking step.

Output goes in the README.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.console import setup as _console_setup  # noqa: E402

_console_setup()

from app.config import settings  # noqa: E402
from ingest.chunking import chunk_type, get_chunker, section_title  # noqa: E402
from ingest.collection_map import collection_for_path, discover_documents  # noqa: E402
from ingest.parse import to_docling_document  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--doc",
        default="claim_submission_guide.md",
        help="Filename to demonstrate (default is the Markdown file - no PDF models needed).",
    )
    parser.add_argument("--n", type=int, default=3, help="How many chunks to show.")
    args = parser.parse_args(argv)

    matches = [p for p in discover_documents(settings.documents_abspath) if p.name == args.doc]
    if not matches:
        print(f"No document named {args.doc!r}.")
        return 1
    path = matches[0]

    chunker = get_chunker()
    print(f"chunker.max_tokens = {chunker.max_tokens}  "
          f"(set on the tokenizer; HybridChunker(max_tokens=...) is silently ignored)")
    print(f"document           = {path.name}  collection={collection_for_path(path).value}\n")

    doc = to_docling_document(path)
    chunks = list(chunker.chunk(dl_doc=doc))

    shown = 0
    for chunk in chunks:
        if not getattr(chunk.meta, "headings", None):
            continue  # a chunk with no heading proves nothing either way
        embedded = chunker.contextualize(chunk=chunk)
        if embedded.strip() == chunk.text.strip():
            continue  # nothing was prepended; not an interesting example

        print("=" * 78)
        print(f"chunk_type    : {chunk_type(chunk)}")
        print(f"section_title : {section_title(chunk)}")
        print()
        print("--- chunk.text (STORED and CITED) " + "-" * 43)
        print(chunk.text[:400])
        print()
        print("--- contextualize(chunk) (EMBEDDED) " + "-" * 42)
        print(embedded[:520])
        print()

        prefix = embedded[: len(embedded) - len(chunk.text)]
        headings_present = all(h.strip() in prefix for h in chunk.meta.headings)
        print(f"heading chain present in the embedded prefix: {headings_present}")
        print(f"  headings : {list(chunk.meta.headings)}")
        print(f"  prefix   : {prefix.strip()!r}")
        print()

        shown += 1
        if shown >= args.n:
            break

    if not shown:
        print("No chunk in this document had a heading chain to prepend.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
