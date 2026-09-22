"""Hierarchical, token-aware chunking via Docling's `HybridChunker`.

`HybridChunker` is hierarchical-first and token-aware-second, which is exactly
the two-pass strategy the assignment specifies: it splits along the document's
own structure (section -> subsection -> paragraph/table), then applies the token
limit as a refinement.

The chunk's *embedded* text is not the raw paragraph. `contextualize()` prepends
the full heading chain, so a chunk reading "25mg twice daily" becomes something
both the embedder and the LLM can actually use. We embed the contextualized form
and store/cite `chunk.text`.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.labels import DocItemLabel
from transformers import AutoTokenizer

from app.config import settings

log = logging.getLogger(__name__)


class ChunkerMisconfigured(RuntimeError):
    """Raised when the token limit did not take effect.

    `HybridChunker(max_tokens=...)` is SILENTLY IGNORED when a real
    `BaseTokenizer` is passed - `max_tokens` is a read-only property that reads
    from the tokenizer. No exception, no warning, and chunks come out at the
    tokenizer's default length instead of the one you asked for. The startup
    assertion below is the only thing that catches it.
    """


@lru_cache(maxsize=1)
def get_chunker() -> HybridChunker:
    """The shared chunker. Constructed once - the tokenizer load is not free."""
    tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(settings.embed_model),
        max_tokens=settings.max_tokens,  # <- on the TOKENIZER, not the chunker
    )
    chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)

    if chunker.max_tokens != settings.max_tokens:
        raise ChunkerMisconfigured(
            f"Expected max_tokens={settings.max_tokens}, got {chunker.max_tokens}. "
            f"The limit must be set on the tokenizer; HybridChunker(max_tokens=...) "
            f"is silently discarded."
        )

    log.info(
        "HybridChunker ready (tokenizer=%s, max_tokens=%d, merge_peers=True)",
        settings.embed_model,
        chunker.max_tokens,
    )
    return chunker


# ---------------------------------------------------------------------------
# chunk_type
# ---------------------------------------------------------------------------

_CHUNK_TYPE: dict[DocItemLabel, str] = {
    DocItemLabel.TABLE: "table",
    DocItemLabel.CODE: "code",
    DocItemLabel.TITLE: "heading",
    DocItemLabel.SECTION_HEADER: "heading",
}

# Priority order, NOT document order. `merge_peers=True` can put a
# SECTION_HEADER and a TABLE in the same chunk; a first-match loop over
# doc_items would type that chunk "heading" and lose the fact that it carries a
# table. Structure-bearing labels win over incidental ones.
_PRIORITY: tuple[DocItemLabel, ...] = (
    DocItemLabel.TABLE,
    DocItemLabel.CODE,
    DocItemLabel.TITLE,
    DocItemLabel.SECTION_HEADER,
)


def chunk_type(chunk) -> str:
    """One of `text`, `table`, `heading`, `code` - the assignment's schema."""
    labels = {item.label for item in getattr(chunk.meta, "doc_items", []) or []}
    for label in _PRIORITY:
        if label in labels:
            return _CHUNK_TYPE[label]
    return "text"


def section_title(chunk) -> str:
    """The heading path, joined so it reads naturally in the UI.

    "Insurance Billing > Claim Rejection Codes" rather than a bare leaf heading.
    """
    headings = getattr(chunk.meta, "headings", None) or []
    return " > ".join(h.strip() for h in headings if h and h.strip())


def source_document(chunk, fallback_name: str) -> str:
    """`chunk.meta.origin` is Optional - guard it."""
    origin = getattr(chunk.meta, "origin", None)
    if origin is not None and getattr(origin, "filename", None):
        return origin.filename
    return fallback_name


def contextualize(chunk) -> str:
    """The text that actually gets embedded: heading chain + body.

    Verified behaviour: `contextualize()` dumps `chunk.meta` excluding
    [schema_name, version, doc_items, origin], joins the surviving list fields
    with the delimiter, and appends `chunk.text` last. What survives is
    `headings`.

    Two caveats worth knowing: it emits the ENTIRE ancestor chain, not just the
    immediate parent; and `HybridChunker` counts the contextualized length
    against the token budget, so a deeply nested document with long headings can
    have its headings dropped for an oversized chunk.
    """
    return get_chunker().contextualize(chunk=chunk)
