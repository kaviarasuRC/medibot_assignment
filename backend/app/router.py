"""Route a question to the SQL branch or the document branch.

Deliberately simple and inspectable: two independent cues must BOTH fire.

Requiring an aggregation cue *and* a database entity avoids the common failure
where "how many mg of amiodarone" routes to SQL - "how many" alone is not
evidence that the answer lives in a table. If this proves too brittle, swap in a
one-shot LLM classifier behind the same `route()` signature; the interface is
designed so that is a one-function change.
"""

from __future__ import annotations

import re
from enum import Enum


class RetrievalRoute(str, Enum):
    SQL_RAG = "sql_rag"
    HYBRID_RAG = "hybrid_rag"


# Aggregation / analytics cues.
_ANALYTICAL = re.compile(
    r"\b(how many|how much|count|number of|total|sum|average|avg|mean|"
    r"percentage|percent|proportion|ratio|most|least|highest|lowest|"
    r"top \d+|breakdown|distribution|trend|per month|per department|"
    r"by department|by category|by status|by issue type|by insurer|"
    r"group(?:ed)? by)\b",
    re.IGNORECASE,
)

# Entities that only exist in mediassist.db, never in a PDF. Drawn from the
# actual schema (see data/DATA_NOTES.md), not guessed.
_SQL_ENTITIES = re.compile(
    r"\b(claims?|claimed|reimbursements?|cashless|insurers?|"
    r"tickets?|maintenance|escalat\w*|"
    r"approved amount|claimed amount|resolution time|"
    r"maintenance_tickets|claims table)\b",
    re.IGNORECASE,
)


def route(question: str) -> RetrievalRoute:
    """SQL only when an aggregation cue AND a database entity are both present."""
    if _ANALYTICAL.search(question) and _SQL_ENTITIES.search(question):
        return RetrievalRoute.SQL_RAG
    return RetrievalRoute.HYBRID_RAG


def explain(question: str) -> dict[str, str | bool]:
    """Why a question routed the way it did - surfaced in logs and tests."""
    analytical = _ANALYTICAL.search(question)
    entity = _SQL_ENTITIES.search(question)
    return {
        "analytical_cue": analytical.group(0) if analytical else "",
        "sql_entity": entity.group(0) if entity else "",
        "routed_to": route(question).value,
    }
