"""Tests for the two-cue analytical router."""

from __future__ import annotations

import pytest

from app.router import RetrievalRoute, explain, route


@pytest.mark.parametrize(
    "question",
    [
        "How many claims were escalated in 2024?",
        "Which equipment category has the most open maintenance tickets?",
        "What is the total claimed amount by department, highest first?",
        "What percentage of claims are still pending?",
        "What is the average resolution time for maintenance tickets by issue type?",
        "count the number of rejected claims",
        "breakdown of tickets by status",
        "which insurer has the highest total claimed amount?",
    ],
)
def test_analytical_questions_route_to_sql(question: str):
    assert route(question) is RetrievalRoute.SQL_RAG, explain(question)


@pytest.mark.parametrize(
    "question",
    [
        # The classic false positive: an aggregation cue with no DB entity.
        "How many mg of amiodarone for an adult in cardiac arrest?",
        "how much paracetamol can be given per day?",
        "How many days of annual leave do I get?",
        "What is the total dose of adrenaline in the protocol?",
        # Conceptual - no aggregation cue at all.
        "What is the hand hygiene protocol in the ICU?",
        "What is the escalation path for a rejected claim?",
        "What size IV cannula for a paediatric patient under 5kg?",
        "How do I calibrate the RadiPro MX-150?",
        "What is the code of conduct on accepting gifts?",
    ],
)
def test_document_questions_route_to_hybrid(question: str):
    assert route(question) is RetrievalRoute.HYBRID_RAG, explain(question)


@pytest.mark.parametrize(
    "question",
    [
        # Regression: `escalat\w*` used to be treated as a database entity, so
        # this nursing question was refused at the SQL gate. "Escalate" is
        # ordinary clinical vocabulary.
        "How many cannulation attempts may one nurse make before escalating?",
        "How many failed attempts before I escalate to a doctor?",
        "What is the escalation procedure for a critical lab value?",
        "How many hours before escalating a pressure injury?",
        # Regression: bare `maintenance` matched the equipment manual, which is
        # a document, not a table.
        "How many preventive maintenance tasks are scheduled monthly?",
        "What is the preventive maintenance schedule for the autoclave?",
    ],
)
def test_clinical_and_equipment_vocabulary_does_not_route_to_sql(question: str):
    assert route(question) is RetrievalRoute.HYBRID_RAG, explain(question)


@pytest.mark.parametrize(
    "question",
    [
        # ...but genuine analytics still routes, because it names a table.
        "How many claims were escalated in 2024?",
        "Which equipment category has the most open maintenance tickets?",
        "Which campus has the most escalated tickets?",
    ],
)
def test_genuine_analytics_still_routes_to_sql(question: str):
    assert route(question) is RetrievalRoute.SQL_RAG, explain(question)


def test_both_cues_are_required():
    # Aggregation cue alone -> documents.
    assert route("how many steps are in the procedure?") is RetrievalRoute.HYBRID_RAG
    # Entity alone -> documents. "What is a cashless claim?" is answered by the
    # billing guide, not by counting rows.
    assert route("what is a cashless claim?") is RetrievalRoute.HYBRID_RAG
    # Both -> SQL.
    assert route("how many cashless claims are there?") is RetrievalRoute.SQL_RAG


def test_explain_reports_the_matched_cues():
    detail = explain("How many claims were escalated?")
    assert detail["analytical_cue"].lower() == "how many"
    assert detail["sql_entity"].lower() in {"claims", "escalated"}
    assert detail["routed_to"] == "sql_rag"


def test_routing_is_case_insensitive():
    assert route("HOW MANY CLAIMS ARE PENDING?") is RetrievalRoute.SQL_RAG
