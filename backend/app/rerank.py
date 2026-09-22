"""Cross-encoder reranking: 20 candidates in, 3 out.

Hybrid retrieval scores the query and each chunk *independently* - the
embeddings are computed without knowledge of each other. A cross-encoder reads
the pair *together* in one forward pass, which is far more accurate and far too
slow to run over a whole corpus. Running it on 20 candidates buys most of the
accuracy for none of the cost.

This is a QUALITY narrowing, not a policy one. Every candidate reaching this
module has already passed the RBAC pre-filter; changing `top_k` changes answer
quality and never who can see what.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import torch
from sentence_transformers import CrossEncoder

from app.chunk import Chunk
from app.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    log.info("Loading cross-encoder: %s", settings.rerank_model)
    return CrossEncoder(
        settings.rerank_model,
        # Verified in the sentence-transformers source: the default activation
        # for these models is already Sigmoid, because num_labels == 1 for every
        # ms-marco cross-encoder. The widely-repeated claim that they "emit raw
        # logits" is wrong for this library. We pass it explicitly anyway - it
        # costs nothing, it documents the (0, 1) score range at the call site,
        # and it survives a swap to a model whose config declares a different
        # default. A relevance floor is then defensible rather than accidental.
        activation_fn=torch.nn.Sigmoid(),
        # NOTE: the kwarg is `max_length`, NOT `max_seq_length`.
        # DESIGN.md sec 7.1 claims v5 renamed it; verified against the installed
        # sentence-transformers 6.1.0, `max_seq_length` is not in
        # CrossEncoder.__init__ at all and passing it raises TypeError.
        max_length=512,
        device="cpu",
    )


def warm() -> None:
    get_reranker()


def _pair_text(chunk: Chunk) -> str:
    """What the cross-encoder actually reads.

    The heading chain is prepended for the same reason `contextualize()` does it
    at ingestion: a chunk body like "Reconsideration must be filed within the
    insurer's window" is far easier to match against "the insurer refused to
    pay" when it is prefixed by "Claim Rejection Response > Deadlines".

    Measured on the probe set in `scripts/compare_retrieval.py`: scoring the
    bare `chunk.text` made reranking a net *regression* against plain hybrid
    (6/8 vs 7/8 hit@3), because the reranker demoted a correct conceptual match
    whose signal lived in its heading. Feeding it the same context the embedder
    saw fixes that.
    """
    if chunk.section_title:
        return f"{chunk.section_title}\n{chunk.text}"
    return chunk.text


def rerank(
    question: str,
    candidates: list[Chunk],
    top_k: int | None = None,
) -> list[tuple[float, Chunk]]:
    """Score every candidate against the query jointly, return the best `top_k`.

    Returns `(score, chunk)` pairs in descending score order. Scores are in
    (0, 1) because of the sigmoid above.
    """
    top_k = top_k or settings.rerank_top_k

    if not candidates:
        return []

    pairs = [(question, _pair_text(c)) for c in candidates]
    scores = get_reranker().predict(pairs, batch_size=32)

    ranked = sorted(
        ((float(s), c) for s, c in zip(scores, candidates)),
        key=lambda pair: -pair[0],
    )

    if settings.log_rerank:
        _log_table(question, ranked)

    return ranked[:top_k]


def _log_table(question: str, ranked: list[tuple[float, Chunk]]) -> None:
    """The artifact worth screenshotting: hybrid rank -> rerank score -> new rank.

    You will regularly see the 4th or 5th hybrid result outscore the 1st. That
    is reranking doing work, rather than a claim that it does.
    """
    lines = [
        "",
        f'rerank  query: "{question}"',
        f"  {'hybrid_rank':>11}  {'rerank_score':>12}  {'new_rank':>8}  section_title",
        f"  {'-' * 11}  {'-' * 12}  {'-' * 8}  {'-' * 44}",
    ]
    for new_rank, (score, chunk) in enumerate(ranked, start=1):
        title = (chunk.section_title or chunk.source_document)[:44]
        moved = "  <-- moved up" if chunk.hybrid_rank > new_rank else ""
        lines.append(
            f"  {chunk.hybrid_rank:>11}  {score:>12.4f}  {new_rank:>8}  {title}{moved}"
        )
    log.info("\n".join(lines))
