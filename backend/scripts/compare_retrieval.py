"""Dense-only vs BM25-only vs hybrid vs hybrid+rerank, with a pass criterion.

    uv run python scripts/compare_retrieval.py

The rubric asks for retrieval quality "demonstrably better than dense-only".
"Demonstrably" needs a number a reviewer can read without domain knowledge, so
each probe carries a hand-labelled correct chunk and the script reports
**hit@3** per configuration plus the mean rank of that chunk.

Probe selection matters. These are not the queries from DESIGN.md §6.4 - that
list was written before the corpus was inspected and includes `amiodarone`,
which appears in **zero** chunks, and a `Fresenius 4008S` that is not the
equipment in this dataset. Every probe below was verified to have exactly one
correct answer in the indexed corpus.

Each probe runs as a role that is permitted to see its answer, so the comparison
measures retrieval quality and not the access filter.

Writes `docs/retrieval_comparison.md`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.console import setup as _console_setup  # noqa: E402

_console_setup()

from app.chunk import Chunk  # noqa: E402
from app.config import REPO_ROOT, settings  # noqa: E402
from app.rbac import Role  # noqa: E402
from app.rerank import rerank  # noqa: E402
from app.retrieval import dense_search, hybrid_search, sparse_search  # noqa: E402

OUTPUT = REPO_ROOT / "docs" / "retrieval_comparison.md"
TOP_N = 3


@dataclass
class Probe:
    query: str
    expected_document: str
    probes_for: str
    # Exactly one of these identifies the correct chunk.
    expected_substring: str = ""
    expected_section: str = ""
    role: Role = Role.ADMIN


# All probes run as `admin`, which can see all 256 chunks. That is deliberate:
# it is the hardest setting, because every chunk in the corpus competes. Running
# as a narrower role would make retrieval look better than it is by quietly
# removing most of the distractors.
PROBES: list[Probe] = [
    # --- Bare exact tokens: where dense search is expected to break ---------
    Probe(
        query="N95",
        expected_document="infection_control.pdf",
        expected_substring="N95",
        probes_for="Bare respirator designation, no semantic content",
    ),
    Probe(
        query="SP3000",
        expected_document="equipment_manual.pdf",
        expected_substring="SP3000",
        probes_for="Equipment model code as written on the asset label",
    ),
    Probe(
        query="J44.1",
        expected_document="billing_codes.pdf",
        expected_substring="J44.1",
        probes_for="Bare ICD-10 code - near-meaningless to a dense embedder",
    ),
    Probe(
        query="M17.0",
        expected_document="billing_codes.pdf",
        expected_substring="M17.0",
        probes_for="Second ICD-10 code, to show the first was not a fluke",
    ),
    Probe(
        query="ICD-10 code I21.4",
        expected_document="billing_codes.pdf",
        expected_substring="I21.4",
        probes_for="Code with a little surrounding context",
    ),
    # --- Paraphrase: where keyword search is expected to break --------------
    Probe(
        query="the insurer refused to pay, what do we do now",
        expected_document="claim_submission_guide.md",
        expected_section="4. Claim Rejection Response",
        probes_for="Paraphrase sharing almost no vocabulary with the document",
    ),
    Probe(
        query="what happens if I am unwell and cannot come to work",
        expected_document="leave_policy.pdf",
        expected_section="2. Leave Types and Entitlements",
        probes_for="Conversational phrasing of a policy question",
    ),
    # --- Mixed --------------------------------------------------------------
    Probe(
        query="Which gauge cannula for a paediatric patient under 5 kg?",
        expected_document="icu_nursing_procedures.pdf",
        expected_substring="24G",
        probes_for="Clinical question carrying an exact size and unit",
    ),
]


def is_correct(chunk: Chunk, probe: Probe) -> bool:
    if chunk.source_document != probe.expected_document:
        return False
    if probe.expected_substring:
        return probe.expected_substring.lower() in chunk.text.lower()
    return probe.expected_section.lower() in chunk.section_title.lower()


def rank_of_correct(chunks: list[Chunk], probe: Probe) -> int | None:
    for rank, chunk in enumerate(chunks, start=1):
        if is_correct(chunk, probe):
            return rank
    return None


def to_chunks(points) -> list[Chunk]:
    return [Chunk.from_point(p, hybrid_rank=i) for i, p in enumerate(points, start=1)]


def run_configurations(probe: Probe) -> dict[str, list[Chunk]]:
    limit = settings.retrieval_top_k

    dense = to_chunks(dense_search(probe.query, probe.role, limit=limit))
    sparse = to_chunks(sparse_search(probe.query, probe.role, limit=limit))
    hybrid = to_chunks(hybrid_search(probe.query, probe.role, limit=limit))
    reranked = [c for _score, c in rerank(probe.query, hybrid, top_k=limit)]

    return {
        "dense only": dense,
        "bm25 only": sparse,
        "hybrid": hybrid,
        "hybrid + rerank": reranked,
    }


CONFIGS = ["dense only", "bm25 only", "hybrid", "hybrid + rerank"]


def main() -> int:
    results: dict[str, dict[str, list[Chunk]]] = {}
    for probe in PROBES:
        results[probe.query] = run_configurations(probe)

    # --- scoring ------------------------------------------------------------
    hits: dict[str, int] = {c: 0 for c in CONFIGS}
    ranks: dict[str, list[int]] = {c: [] for c in CONFIGS}
    misses: dict[str, list[str]] = {c: [] for c in CONFIGS}

    for probe in PROBES:
        for config in CONFIGS:
            chunks = results[probe.query][config]
            rank = rank_of_correct(chunks[:TOP_N], probe)
            if rank:
                hits[config] += 1
                ranks[config].append(rank)
            else:
                misses[config].append(probe.query)
                full = rank_of_correct(chunks, probe)
                if full:
                    ranks[config].append(full)

    def mean(values: list[int]) -> str:
        return f"{sum(values) / len(values):.1f}" if values else "-"

    # --- console ------------------------------------------------------------
    print()
    print("=" * 92)
    print(f"RETRIEVAL COMPARISON  -  {len(PROBES)} probes, hit@{TOP_N}")
    print("=" * 92)
    print(f"{'configuration':<20} {'hit@3':<8} {'mean rank of correct chunk':<30} misses")
    print("-" * 92)
    for config in CONFIGS:
        miss = ", ".join(m[:34] for m in misses[config]) or "-"
        print(f"{config:<20} {hits[config]}/{len(PROBES):<6} {mean(ranks[config]):<30} {miss}")
    print("-" * 92)

    print("\nPer-probe rank of the correct chunk (lower is better, '-' = not in top 20)\n")
    header = f"{'probe':<52}" + "".join(f"{c:<18}" for c in CONFIGS)
    print(header)
    print("-" * len(header))
    for probe in PROBES:
        row = f"{probe.query[:50]:<52}"
        for config in CONFIGS:
            rank = rank_of_correct(results[probe.query][config], probe)
            row += f"{(str(rank) if rank else '-'):<18}"
        print(row)
    print()

    # --- markdown -----------------------------------------------------------
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Retrieval Comparison",
        "",
        f"Generated {stamp} by `uv run python scripts/compare_retrieval.py`.",
        "",
        f"{len(PROBES)} probe queries, each with one hand-labelled correct chunk "
        f"verified to exist in the indexed corpus. The metric is **hit@{TOP_N}**: "
        "is the correct chunk in the top 3 a configuration returns?",
        "",
        "Each probe runs as a role permitted to see its answer, so this measures "
        "retrieval quality and not the access filter.",
        "",
        "## Headline",
        "",
        f"| Configuration | hit@{TOP_N} | Mean rank of correct chunk | Misses |",
        "|---|---|---|---|",
    ]
    for config in CONFIGS:
        miss = ", ".join(f"`{m}`" for m in misses[config]) or "*none*"
        lines.append(
            f"| {config} | **{hits[config]}/{len(PROBES)}** | {mean(ranks[config])} | {miss} |"
        )

    lines += [
        "",
        "## Rank of the correct chunk, per probe",
        "",
        "`-` means the correct chunk was not in the top 20 at all.",
        "",
        "| Probe | What it probes | " + " | ".join(CONFIGS) + " |",
        "|---|---|" + "---|" * len(CONFIGS),
    ]
    for probe in PROBES:
        cells = []
        for config in CONFIGS:
            rank = rank_of_correct(results[probe.query][config], probe)
            cells.append(str(rank) if rank else "—")
        lines.append(
            f"| `{probe.query}` | {probe.probes_for} | " + " | ".join(cells) + " |"
        )

    lines += ["", "## Top-3 per configuration", ""]
    for probe in PROBES:
        lines += [
            f"### `{probe.query}`",
            "",
            f"*Role:* `{probe.role.value}` · *Expected:* `{probe.expected_document}` "
            + (f"containing `{probe.expected_substring}`" if probe.expected_substring
               else f"section `{probe.expected_section}`"),
            "",
        ]
        for config in CONFIGS:
            lines.append(f"**{config}**")
            lines.append("")
            for rank, chunk in enumerate(results[probe.query][config][:TOP_N], start=1):
                mark = " ✅" if is_correct(chunk, probe) else ""
                preview = " ".join(chunk.text.split())[:110]
                lines.append(
                    f"{rank}. `{chunk.source_document}` — {chunk.section_title or '(none)'}{mark}  \n"
                    f"   {preview}…"
                )
            lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
