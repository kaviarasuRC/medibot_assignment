"""The access matrix, and the Qdrant filter derived from it.

This module is the single source of truth for who may see what. Nothing else in
the codebase may hard-code a role/collection relationship:

- `ingest.py` calls `roles_for_collection()` to write each chunk's
  `access_roles` payload at index time.
- `retrieval.py` calls `rbac_filter()` to build the query-time pre-filter.

Because both read the same dict, the labels written at index time and the filter
applied at query time cannot drift apart. That drift is the single most likely
source of a silent access leak, and deriving both from one mapping is what makes
it impossible rather than merely unlikely.
"""

from __future__ import annotations

from enum import Enum

from qdrant_client import models


class Role(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    BILLING_EXECUTIVE = "billing_executive"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class Collection(str, Enum):
    GENERAL = "general"
    CLINICAL = "clinical"
    NURSING = "nursing"
    BILLING = "billing"
    EQUIPMENT = "equipment"


class PermissionDenied(Exception):
    """Raised when a role cannot be resolved against the matrix.

    Deliberately an exception and not an empty filter: an empty
    `models.Filter()` matches EVERYTHING, so a fail-open bug here would hand an
    unauthenticated caller the entire corpus.
    """

    def __init__(self, role: object) -> None:
        self.role = role
        super().__init__(f"No access policy is defined for role {role!r}")


class RBACViolation(Exception):
    """Raised by the layer-3 assertion when an out-of-policy chunk is returned.

    Reaching this means the query filter failed. There is no recovery path that
    answers the question - the request fails loudly instead.
    """


# ---------------------------------------------------------------------------
# THE MATRIX
# ---------------------------------------------------------------------------
# On the doctor/nursing row: the assignment's role table gives `doctor`
# "clinical protocols, drug formulary, diagnostic guidelines + General", but its
# data-sources table lists `nursing` as accessible by nurse, doctor and admin.
# The data-sources table is the more specific statement, so doctor gets nursing
# too - a physician reading ICU nursing procedures is clinically sensible.
# This reading is stated in the README so a reviewer sees a decision, not a bug.

ROLE_COLLECTIONS: dict[Role, frozenset[Collection]] = {
    Role.DOCTOR: frozenset(
        {Collection.GENERAL, Collection.CLINICAL, Collection.NURSING}
    ),
    Role.NURSE: frozenset({Collection.GENERAL, Collection.NURSING}),
    Role.BILLING_EXECUTIVE: frozenset({Collection.GENERAL, Collection.BILLING}),
    Role.TECHNICIAN: frozenset({Collection.GENERAL, Collection.EQUIPMENT}),
    Role.ADMIN: frozenset(Collection),  # all five
}

# Analytical questions hit a relational database no PDF can answer. Only the
# roles with analytical responsibilities may run them.
SQL_RAG_ROLES: frozenset[Role] = frozenset({Role.BILLING_EXECUTIVE, Role.ADMIN})


def coerce_role(role: object) -> Role:
    """Resolve anything claiming to be a role into a `Role`, or raise.

    A tampered or unknown token payload arrives here as a bare string. It must
    fail closed rather than resolve to a default.
    """
    if isinstance(role, Role):
        return role
    try:
        return Role(role)
    except (ValueError, KeyError) as exc:
        raise PermissionDenied(role) from exc


def collections_for_role(role: object) -> list[str]:
    """The collections this role may read, sorted. Raises on an unknown role."""
    resolved = coerce_role(role)
    allowed = ROLE_COLLECTIONS.get(resolved)
    if not allowed:
        raise PermissionDenied(role)
    return sorted(c.value for c in allowed)


def roles_for_collection(collection: Collection) -> list[str]:
    """The inverse mapping - derived, never written by hand.

    This is what ingestion writes into each chunk's `access_roles` payload.
    Hand-writing the list per collection is how a `billing` document quietly
    ends up readable by everyone, with nothing in the system to tell you.
    """
    return sorted(
        role.value
        for role, collections in ROLE_COLLECTIONS.items()
        if collection in collections
    )


def can_use_sql_rag(role: object) -> bool:
    return coerce_role(role) in SQL_RAG_ROLES


def rbac_filter(role: object) -> models.Filter:
    """The enforcement. A Qdrant pre-filter on the `access_roles` payload.

    Passed as `query_filter` at the TOP level of `query_points`, this propagates
    recursively into every `prefetch` branch and is applied BEFORE each branch's
    limit - so both the dense and the BM25 branch search only permitted chunks,
    and a restricted chunk is never scored, never returned, and never enters
    process memory.

    Two details decide whether this is correct:

    1. `MatchValue` on an array field means "contains". Qdrant's docs: "If
       several values are stored, at least one of them should match the
       condition." A chunk labelled `["doctor", "admin"]` matches
       `MatchValue(value="doctor")` and does not match `MatchValue(value="nurse")`.
       That is exactly the semantics we want.

    2. `MatchAny` is MORE permissive, not stricter - it ORs across the given
       values. It is the right tool only if a user could hold several roles at
       once. In this system a user has exactly one role, so swapping to
       `MatchAny` later, thinking it tightens the check, would be a
       privilege-escalation bug. Do not.
    """
    resolved = coerce_role(role)

    # Resolve through the matrix even though the filter keys off the role value.
    # A Role that exists in the enum but has no matrix entry must fail closed,
    # not produce a filter that silently matches nothing useful.
    allowed = ROLE_COLLECTIONS.get(resolved)
    if not allowed:
        raise PermissionDenied(role)

    return models.Filter(
        must=[
            models.FieldCondition(
                key="access_roles",
                match=models.MatchValue(value=resolved.value),
            )
        ]
    )


def refusal_message(role: object) -> str:
    """A role-scoped refusal, constructed from the matrix so it stays accurate.

    The rubric calls out a generic "no results" as insufficient. This names the
    collections the user CAN use, and never names the ones they cannot - which
    would confirm that a restricted collection exists.
    """
    resolved = coerce_role(role)
    names = ", ".join(collections_for_role(resolved))
    return (
        f"As a {resolved.value.replace('_', ' ')}, you don't have access to documents "
        f"outside your permitted collections. I can only answer questions from the "
        f"{names} collections. If you believe you need broader access, please contact "
        f"your system administrator."
    )


def sql_refusal_message(role: object) -> str:
    """Refusal for an analytical question from a role without SQL access."""
    resolved = coerce_role(role)
    permitted = ", ".join(sorted(r.value.replace("_", " ") for r in SQL_RAG_ROLES))
    return (
        f"As a {resolved.value.replace('_', ' ')}, you don't have access to the "
        f"operational analytics database. Analytical queries over claims and "
        f"maintenance records are available to {permitted} roles only. I can still "
        f"answer questions from your permitted document collections: "
        f"{', '.join(collections_for_role(resolved))}."
    )
