"""Tests for the cross-encoder reranker.

Downloads ~90 MB on first run, then cached.
"""

from __future__ import annotations

from app.chunk import Chunk
from app.rerank import rerank

RELEVANT = (
    "IV cannula site selection for paediatric patients. For a patient under "
    "5 kg, use a 24G cannula. Select the dorsum of the hand first."
)
IRRELEVANT = (
    "Employees accrue paid leave monthly according to tenure. Carry-forward is "
    "capped at 30 days per calendar year."
)


def chunk(text: str, n: int) -> Chunk:
    return Chunk(
        text=text,
        source_document=f"doc_{n}.pdf",
        collection="nursing",
        section_title=f"Section {n}",
        chunk_type="text",
        hybrid_rank=n,
    )


def test_returns_exactly_top_k():
    candidates = [chunk(IRRELEVANT, i) for i in range(1, 11)]
    assert len(rerank("anything", candidates, top_k=3)) == 3
    assert len(rerank("anything", candidates, top_k=1)) == 1


def test_top_k_larger_than_the_candidate_set_returns_all():
    candidates = [chunk(IRRELEVANT, i) for i in range(1, 3)]
    assert len(rerank("anything", candidates, top_k=10)) == 2


def test_empty_candidates_returns_empty_rather_than_raising():
    assert rerank("anything", [], top_k=3) == []


def test_scores_are_in_the_unit_interval():
    """Proves the sigmoid is applied - which is what makes a relevance floor
    like 0.05 defensible rather than accidental."""
    candidates = [chunk(RELEVANT, 1), chunk(IRRELEVANT, 2)]
    for score, _ in rerank("IV cannula size", candidates, top_k=2):
        assert 0.0 <= score <= 1.0


def test_results_are_sorted_by_descending_score():
    candidates = [chunk(IRRELEVANT, 1), chunk(RELEVANT, 2), chunk(IRRELEVANT, 3)]
    scores = [s for s, _ in rerank("IV cannula size for a small child", candidates, top_k=3)]
    assert scores == sorted(scores, reverse=True)


def test_reranking_actually_reorders():
    """The relevant chunk is placed LAST in hybrid order and must come first."""
    candidates = [
        chunk(IRRELEVANT, 1),
        chunk(IRRELEVANT, 2),
        chunk(RELEVANT, 3),
    ]
    ranked = rerank("What size IV cannula for a patient under 5kg?", candidates, top_k=3)
    top_score, top_chunk = ranked[0]
    assert top_chunk.text == RELEVANT
    assert top_chunk.hybrid_rank == 3, "the 3rd hybrid result became the 1st"
    assert top_score > ranked[-1][0]


def test_an_unrelated_query_scores_below_the_relevance_floor():
    from app.config import settings

    candidates = [chunk(IRRELEVANT, 1)]
    (score, _), = rerank("amiodarone loading dose in cardiac arrest", candidates, top_k=1)
    assert score < settings.rerank_min_score


def test_a_weakly_phrased_but_correct_match_stays_above_the_floor():
    """Regression: the floor must not refuse answers the user is entitled to.

    The first floor here was 0.05, chosen on the reasoning that a relevant
    passage scores 0.5-0.99. That holds for well-phrased questions only. This
    chunk is the correct answer and still scores ~0.006, because cross-encoder
    scores are not calibrated across queries - so 0.05 refused it.

    A false refusal is the dangerous direction: it looks exactly like RBAC
    working correctly. See scripts/calibrate_floor.py.
    """
    from app.config import settings

    maintenance = Chunk(
        text=(
            "- After each patient use: clean with 70% IPA. - Weekly: functional check "
            "by the department. - 6-monthly: full preventive maintenance by biomedical "
            "engineering. - Annually: performance verification and safety test."
        ),
        source_document="equipment_manual.pdf",
        collection="equipment",
        section_title="Maintenance schedule",
        chunk_type="text",
    )
    (score, _), = rerank(
        "What is the preventive maintenance schedule for the autoclave?",
        [maintenance],
        top_k=1,
    )
    assert score >= settings.rerank_min_score, (
        f"correct answer scored {score:.6f}, below the floor "
        f"{settings.rerank_min_score} - re-run scripts/calibrate_floor.py"
    )


def test_the_floor_sits_between_the_measured_bands():
    """Lock the calibration recorded in docs/rerank_floor_calibration.md."""
    from app.config import settings

    highest_correct_refusal = 0.000323
    lowest_correct_answer = 0.005906
    assert highest_correct_refusal < settings.rerank_min_score < lowest_correct_answer
