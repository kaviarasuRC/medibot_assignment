"""Tests for prompt assembly, citation building, and the refusal path.

All offline. The plan asks for a hand-built 3-chunk fixture asserting the prompt
contains all three sources and the role - no network involved.
"""

from __future__ import annotations

from app.chunk import Chunk
from app.generate import SYSTEM_PROMPT, build_context, build_sources, generate_answer
from app.rbac import Role, refusal_message


def make_chunk(n: int, collection: str = "nursing") -> Chunk:
    return Chunk(
        text=f"Body text number {n}.",
        source_document=f"doc_{n}.pdf",
        collection=collection,
        section_title=f"Section {n} > Subsection {n}",
        chunk_type="text",
        access_roles=("admin", "doctor", "nurse"),
        hybrid_rank=n,
    )


FIXTURE = [(0.9, make_chunk(1)), (0.8, make_chunk(2)), (0.7, make_chunk(3))]


# --- Context block ----------------------------------------------------------


def test_context_numbers_every_chunk_and_shows_both_citation_fields():
    context = build_context(FIXTURE)
    for n in (1, 2, 3):
        assert f"[{n}]" in context
        assert f"doc_{n}.pdf" in context
        assert f"Section {n} > Subsection {n}" in context
        assert f"Body text number {n}." in context


def test_context_shows_the_fields_in_the_format_the_model_is_asked_to_cite():
    context = build_context(FIXTURE)
    assert "source_document:" in context
    assert "section_title:" in context


def test_prompt_states_the_role_and_all_five_rules():
    prompt = SYSTEM_PROMPT.format(role=Role.NURSE.value)
    assert "nurse" in prompt
    for n in range(1, 6):
        assert f"{n}." in prompt
    # Rule 5 is the one people omit; without it the model names restricted
    # collections it cannot see.
    assert "never comment on what" in prompt.lower()
    assert "only from the context" in prompt.lower()


def test_context_handles_a_chunk_with_no_heading():
    chunk = Chunk(
        text="Orphan paragraph.",
        source_document="x.pdf",
        collection="general",
        section_title="",
        chunk_type="text",
    )
    assert "(none)" in build_context([(0.5, chunk)])


# --- Sources ----------------------------------------------------------------


def test_sources_are_built_from_the_chunks_not_parsed_from_prose():
    sources = build_sources(FIXTURE)
    assert [s.source_document for s in sources] == ["doc_1.pdf", "doc_2.pdf", "doc_3.pdf"]
    assert all(s.collection == "nursing" for s in sources)
    assert sources[0].section_title == "Section 1 > Subsection 1"


def test_sources_are_deduplicated_on_document_and_section():
    duplicate = [(0.9, make_chunk(1)), (0.8, make_chunk(1)), (0.7, make_chunk(2))]
    sources = build_sources(duplicate)
    assert len(sources) == 2


def test_two_chunks_from_one_document_but_different_sections_stay_separate():
    a = make_chunk(1)
    b = Chunk(
        text="Other section.",
        source_document="doc_1.pdf",
        collection="nursing",
        section_title="Section 9",
        chunk_type="text",
    )
    assert len(build_sources([(0.9, a), (0.8, b)])) == 2


# --- Refusal path -----------------------------------------------------------


def test_empty_chunks_returns_the_refusal_without_calling_the_llm():
    """No GROQ_API_KEY is needed - the LLM is never reached on this path.

    That is what makes the refusal text deterministic and therefore assertable
    in the adversarial suite.
    """
    answer, sources = generate_answer("show me the billing codes", Role.NURSE, [])
    assert answer == refusal_message(Role.NURSE)
    assert sources == []


def test_refusal_is_role_specific():
    nurse, _ = generate_answer("q", Role.NURSE, [])
    tech, _ = generate_answer("q", Role.TECHNICIAN, [])
    assert nurse != tech
    assert "nursing" in nurse and "equipment" in tech
