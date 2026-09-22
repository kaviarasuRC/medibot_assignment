"""Calibrate RERANK_MIN_SCORE against labelled should-answer / should-refuse cases.

    uv run python scripts/calibrate_floor.py

Why this exists: cross-encoder scores are **not calibrated across queries**. The
model is sharply bimodal - a confident match scores ~0.98 and everything else
~0.000x - but the exact value for a *weakly* phrased correct match varies by an
order of magnitude. So any fixed relevance floor is an empirical choice, and it
needs to be re-derived rather than guessed whenever the corpus, the embedder or
the reranker changes.

The floor's job is narrow: decide whether ANY permitted chunk is on-topic. Below
it, MediBot returns the role-scoped refusal instead of letting the LLM improvise
from loosely-related text.

Getting it wrong is asymmetric and the two failures look completely different:

  - too HIGH -> correct answers are refused. This is the dangerous one, because
    a false refusal is indistinguishable from RBAC working correctly. It was
    exactly this: an initial guess of 0.05 refused a nurse the cannula
    escalation procedure she is entitled to read.
  - too LOW  -> the LLM is handed irrelevant context and may improvise.

Writes `docs/rerank_floor_calibration.md`.
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

OUTPUT = REPO_ROOT / "docs" / "rerank_floor_calibration.md"

# (question, role, should_answer)
CASES: list[tuple[str, Role, bool]] = [
    # --- Must REFUSE: the answer lives in a collection this role cannot see ---
    ("What is the standard dosage of amiodarone for adult cardiac arrest?", Role.TECHNICIAN, False),
    ("Show me all insurance billing codes", Role.NURSE, False),
    ("What is the package rate for a pacemaker implant?", Role.NURSE, False),
    ("What are the normal arterial blood gas ranges?", Role.NURSE, False),
    ("Which fault codes require removing the X-ray unit?", Role.DOCTOR, False),
    ("What is the ventilator bundle for VAP prevention?", Role.BILLING_EXECUTIVE, False),
    ("What is the standard dose of amlodipine?", Role.TECHNICIAN, False),
    ("How do I insert a nasogastric tube?", Role.TECHNICIAN, False),

    # --- Must ANSWER: in-policy, and the corpus genuinely contains it ---
    # The first two are weakly-phrased on purpose - they are the hard cases that
    # sit closest to the boundary.
    ("What is the escalation procedure if a cannula site looks infected?", Role.NURSE, True),
    ("What is the preventive maintenance schedule for the autoclave?", Role.TECHNICIAN, True),
    ("How many cannulation attempts before escalating?", Role.NURSE, True),
    ("What colour bin is used for biomedical waste?", Role.NURSE, True),
    ("What is the carry-forward cap on earned leave?", Role.TECHNICIAN, True),
    ("What is the default occlusion pressure alarm?", Role.TECHNICIAN, True),
    ("What defines an outbreak?", Role.NURSE, True),
    ("What is the normal haemoglobin range for a male?", Role.DOCTOR, True),
    ("What is the appeal deadline for a rejected claim?", Role.BILLING_EXECUTIVE, True),
    ("What does fault code E-01 mean on the autoclave?", Role.TECHNICIAN, True),
]


def top_score(question: str, role: Role) -> float:
    points = hybrid_search(question, role, limit=settings.retrieval_top_k)
    candidates = [Chunk.from_point(p, hybrid_rank=i) for i, p in enumerate(points, start=1)]
    ranked = rerank(question, candidates, top_k=1)
    return ranked[0][0] if ranked else 0.0


def main() -> int:
    results: list[tuple[str, Role, bool, float]] = []
    for question, role, should_answer in CASES:
        results.append((question, role, should_answer, top_score(question, role)))

    refuse = [s for _q, _r, ans, s in results if not ans]
    answer = [s for _q, _r, ans, s in results if ans]
    refuse_max, answer_min = max(refuse), min(answer)
    separable = refuse_max < answer_min
    # Geometric midpoint - equal multiplicative margin on both sides.
    suggested = (refuse_max * answer_min) ** 0.5

    print()
    print("=" * 104)
    print(f"RELEVANCE FLOOR CALIBRATION   (current RERANK_MIN_SCORE = {settings.rerank_min_score})")
    print("=" * 104)
    print(f"{'expected':<10}{'role':<20}{'top score':>12}  {'verdict':<10}question")
    print("-" * 104)
    for question, role, should_answer, score in sorted(results, key=lambda r: r[3]):
        passes = score >= settings.rerank_min_score
        correct = passes == should_answer
        print(
            f"{('ANSWER' if should_answer else 'REFUSE'):<10}{role.value:<20}{score:>12.6f}  "
            f"{('ok' if correct else 'WRONG <<<'):<10}{question[:44]}"
        )
    print("-" * 104)
    print(f"highest score among SHOULD-REFUSE : {refuse_max:.6f}")
    print(f"lowest  score among SHOULD-ANSWER : {answer_min:.6f}")
    print(f"separable                         : {separable}")
    print(f"suggested floor (geometric mid)   : {suggested:.6f}")
    print(f"margin below lowest answer        : {answer_min / settings.rerank_min_score:.1f}x")
    print(f"margin above highest refusal      : {settings.rerank_min_score / refuse_max:.1f}x")

    wrong = [
        (q, r, a, s)
        for q, r, a, s in results
        if (s >= settings.rerank_min_score) != a
    ]
    print(f"misclassified at the current floor: {len(wrong)}")
    for q, r, a, s in wrong:
        print(f"    {('should ANSWER' if a else 'should REFUSE')}  {s:.6f}  [{r.value}] {q}")
    print("=" * 104)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Relevance Floor Calibration",
        "",
        f"Generated {stamp} by `uv run python scripts/calibrate_floor.py`.",
        "",
        f"Current `RERANK_MIN_SCORE` = **{settings.rerank_min_score}**",
        "",
        "Cross-encoder scores are **not calibrated across queries**. The model is",
        "sharply bimodal — a confident match scores ~0.98, an unrelated chunk ~0.000x —",
        "but a *weakly phrased* correct match can land an order of magnitude lower than",
        "a well-phrased one. So the floor is an empirical choice and has to be",
        "re-derived whenever the corpus, the embedder or the reranker changes.",
        "",
        "Getting it wrong is asymmetric, and the two failures look nothing alike:",
        "",
        "- **Too high** → correct answers are refused. This is the dangerous direction,",
        "  because a false refusal is visually identical to RBAC working correctly.",
        "- **Too low** → the LLM is handed irrelevant context and may improvise.",
        "",
        "| Expected | Role | Top rerank score | Verdict | Question |",
        "|---|---|---:|---|---|",
    ]
    for question, role, should_answer, score in sorted(results, key=lambda r: r[3]):
        passes = score >= settings.rerank_min_score
        verdict = "✅" if passes == should_answer else "❌"
        lines.append(
            f"| {'ANSWER' if should_answer else 'REFUSE'} | `{role.value}` | "
            f"{score:.6f} | {verdict} | {question} |"
        )

    lines += [
        "",
        "## Separation",
        "",
        f"| Metric | Value |",
        "|---|---|",
        f"| Highest score among should-refuse | `{refuse_max:.6f}` |",
        f"| Lowest score among should-answer | `{answer_min:.6f}` |",
        f"| Separable | **{separable}** |",
        f"| Suggested floor (geometric midpoint) | `{suggested:.6f}` |",
        f"| Configured floor | `{settings.rerank_min_score}` |",
        f"| Margin below the lowest correct answer | {answer_min / settings.rerank_min_score:.1f}× |",
        f"| Margin above the highest correct refusal | {settings.rerank_min_score / refuse_max:.1f}× |",
        f"| Misclassified at the configured floor | **{len(wrong)}** |",
        "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUTPUT.relative_to(REPO_ROOT)}")

    return 0 if not wrong else 1


if __name__ == "__main__":
    raise SystemExit(main())
