"""Show the reranker doing work: hybrid rank -> rerank score -> new rank.

    uv run python scripts/rerank_demo.py

The assignment's tip is that you will regularly see the 4th or 5th retrieved
chunk score higher than the 1st. This prints the full 20-candidate table per
query so that movement is visible rather than asserted.

Writes `docs/rerank_log.md`.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.console import setup as _console_setup  # noqa: E402

_console_setup()

from app.chunk import Chunk  # noqa: E402
from app.config import REPO_ROOT, settings  # noqa: E402
from app.rbac import Role  # noqa: E402
from app.rerank import rerank  # noqa: E402
from app.retrieval import hybrid_search  # noqa: E402

OUTPUT = REPO_ROOT / "docs" / "rerank_log.md"

QUERIES: list[tuple[str, Role]] = [
    ("What size cannula should I use for a baby under 5 kg?", Role.NURSE),
    ("N95", Role.NURSE),
    ("How do I respond when an insurer rejects a claim?", Role.BILLING_EXECUTIVE),
    ("Which fault codes mean the X-ray unit must be removed from service?", Role.TECHNICIAN),
    ("How much earned leave do clinical staff get?", Role.DOCTOR),
]


def run(query: str, role: Role) -> tuple[list[tuple[float, Chunk]], int]:
    points = hybrid_search(query, role, limit=settings.retrieval_top_k)
    candidates = [Chunk.from_point(p, hybrid_rank=i) for i, p in enumerate(points, start=1)]
    ranked = rerank(query, candidates, top_k=len(candidates))
    biggest = max((c.hybrid_rank - i for i, (_s, c) in enumerate(ranked, start=1)), default=0)
    return ranked, biggest


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Cross-Encoder Reranking Log",
        "",
        f"Generated {stamp} by `uv run python scripts/rerank_demo.py`.",
        "",
        "Hybrid retrieval scores the query and each chunk **independently** - the two",
        "embeddings are computed without knowledge of each other. A cross-encoder reads",
        "the pair **together** in one forward pass. That is far more accurate, and far",
        "too slow to run over a whole corpus, which is why it runs on 20 candidates",
        "rather than 256 chunks.",
        "",
        f"Only the top {settings.rerank_top_k} after reranking are passed to the LLM, and",
        "only if they clear the relevance floor. Rows in **bold** are the ones that",
        "actually reached the prompt.",
        "",
        f"Scores are in (0, 1) because the model is loaded with an explicit sigmoid "
        f"activation. The relevance floor is `{settings.rerank_min_score}` - below it, "
        "the role-scoped refusal is returned instead of an answer.",
        "",
    ]

    for query, role in QUERIES:
        ranked, biggest = run(query, role)
        print("\n" + "=" * 92)
        print(f'QUERY: "{query}"   (role: {role.value})')
        print("=" * 92)
        print(f"  {'hybrid_rank':>11}  {'rerank_score':>12}  {'new_rank':>8}  {'move':>6}  section_title")
        print(f"  {'-'*11}  {'-'*12}  {'-'*8}  {'-'*6}  {'-'*40}")

        lines += [
            f'## `{query}`',
            "",
            f"*Role:* `{role.value}`",
            "",
            "| hybrid rank | rerank score | new rank | move | source | section |",
            "|---|---|---|---|---|---|",
        ]

        for new_rank, (score, chunk) in enumerate(ranked, start=1):
            move = chunk.hybrid_rank - new_rank
            arrow = f"+{move}" if move > 0 else (str(move) if move < 0 else "-")
            title = (chunk.section_title or "(none)")[:48]
            to_llm = new_rank <= settings.rerank_top_k and score >= settings.rerank_min_score
            cut = "  <- to LLM" if to_llm else ""
            print(
                f"  {chunk.hybrid_rank:>11}  {score:>12.4f}  {new_rank:>8}  {arrow:>6}  {title}{cut}"
            )
            bold = "**" if to_llm else ""
            lines.append(
                f"| {chunk.hybrid_rank} | {bold}{score:.4f}{bold} | {bold}{new_rank}{bold} "
                f"| {arrow} | `{chunk.source_document}` | {chunk.section_title or '(none)'} |"
            )

        lines += ["", f"Largest promotion: **{biggest} places**.", ""]
        print(f"\n  Largest promotion: {biggest} places.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
