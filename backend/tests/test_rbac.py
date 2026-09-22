"""Tests for the access matrix.

`IMPLEMENTATION_PLAN.md` §2.1 makes these a gate: nothing else gets built until
they pass, because every downstream component derives its behaviour from this
module.
"""

from __future__ import annotations

import pytest
from qdrant_client import models

from app.rbac import (
    ROLE_COLLECTIONS,
    SQL_RAG_ROLES,
    Collection,
    PermissionDenied,
    Role,
    can_use_sql_rag,
    coerce_role,
    collections_for_role,
    rbac_filter,
    refusal_message,
    roles_for_collection,
    sql_refusal_message,
)

# --- The matrix itself ------------------------------------------------------


def test_every_role_has_a_policy():
    assert set(ROLE_COLLECTIONS) == set(Role)


def test_every_collection_is_reachable_by_at_least_one_role():
    for collection in Collection:
        assert roles_for_collection(collection), f"{collection} is unreachable"


def test_admin_reaches_all_five_collections():
    assert ROLE_COLLECTIONS[Role.ADMIN] == frozenset(Collection)
    assert len(collections_for_role(Role.ADMIN)) == 5


def test_general_is_readable_by_every_role():
    assert roles_for_collection(Collection.GENERAL) == sorted(r.value for r in Role)


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.DOCTOR, ["clinical", "general", "nursing"]),
        (Role.NURSE, ["general", "nursing"]),
        (Role.BILLING_EXECUTIVE, ["billing", "general"]),
        (Role.TECHNICIAN, ["equipment", "general"]),
        (Role.ADMIN, ["billing", "clinical", "equipment", "general", "nursing"]),
    ],
)
def test_collections_per_role(role: Role, expected: list[str]):
    assert collections_for_role(role) == expected


def test_nurse_cannot_reach_billing_or_equipment():
    allowed = ROLE_COLLECTIONS[Role.NURSE]
    assert Collection.BILLING not in allowed
    assert Collection.EQUIPMENT not in allowed
    assert Collection.CLINICAL not in allowed


def test_billing_executive_cannot_reach_clinical_or_nursing():
    allowed = ROLE_COLLECTIONS[Role.BILLING_EXECUTIVE]
    assert Collection.CLINICAL not in allowed
    assert Collection.NURSING not in allowed


def test_technician_reaches_only_equipment_and_general():
    assert ROLE_COLLECTIONS[Role.TECHNICIAN] == frozenset(
        {Collection.EQUIPMENT, Collection.GENERAL}
    )


def test_doctor_gets_nursing_per_the_data_sources_table():
    # Documented spec reading - see the comment above ROLE_COLLECTIONS.
    assert Collection.NURSING in ROLE_COLLECTIONS[Role.DOCTOR]


# --- The inverse mapping is genuinely derived -------------------------------


@pytest.mark.parametrize(
    ("collection", "expected"),
    [
        (Collection.GENERAL, ["admin", "billing_executive", "doctor", "nurse", "technician"]),
        (Collection.CLINICAL, ["admin", "doctor"]),
        (Collection.NURSING, ["admin", "doctor", "nurse"]),
        (Collection.BILLING, ["admin", "billing_executive"]),
        (Collection.EQUIPMENT, ["admin", "technician"]),
    ],
)
def test_roles_for_collection(collection: Collection, expected: list[str]):
    assert roles_for_collection(collection) == expected


def test_forward_and_inverse_mappings_agree():
    """The property that makes an index-time/query-time drift impossible."""
    for role in Role:
        for collection in Collection:
            labelled = role.value in roles_for_collection(collection)
            permitted = collection in ROLE_COLLECTIONS[role]
            assert labelled == permitted, (role, collection)


# --- Fail closed ------------------------------------------------------------


@pytest.mark.parametrize("bad", ["superuser", "", "DOCTOR", None, 0, "admin ", "Admin"])
def test_unknown_role_raises_rather_than_returning_an_empty_filter(bad: object):
    # An empty `models.Filter()` matches EVERYTHING. Returning one here would
    # hand the whole corpus to an unauthenticated caller.
    with pytest.raises(PermissionDenied):
        rbac_filter(bad)
    with pytest.raises(PermissionDenied):
        collections_for_role(bad)


def test_coerce_role_accepts_the_exact_string_values():
    for role in Role:
        assert coerce_role(role.value) is role
        assert coerce_role(role) is role


# --- The filter -------------------------------------------------------------


@pytest.mark.parametrize("role", list(Role))
def test_filter_shape_is_a_single_matchvalue_on_access_roles(role: Role):
    f = rbac_filter(role)

    assert f.must is not None and len(f.must) == 1
    assert not f.should and not f.must_not

    condition = f.must[0]
    assert isinstance(condition, models.FieldCondition)
    assert condition.key == "access_roles"

    # MatchValue on a list-valued field means "contains". MatchAny would be an
    # OR across values - more permissive, and a privilege-escalation bug here.
    assert isinstance(condition.match, models.MatchValue)
    assert not isinstance(condition.match, models.MatchAny)
    assert condition.match.value == role.value


def test_filter_never_produces_an_empty_filter():
    for role in Role:
        f = rbac_filter(role)
        assert f.must, "an empty Filter matches everything"


# --- SQL RAG gate -----------------------------------------------------------


def test_sql_rag_is_limited_to_analytical_roles():
    assert SQL_RAG_ROLES == frozenset({Role.BILLING_EXECUTIVE, Role.ADMIN})
    assert can_use_sql_rag(Role.BILLING_EXECUTIVE)
    assert can_use_sql_rag(Role.ADMIN)
    for role in (Role.DOCTOR, Role.NURSE, Role.TECHNICIAN):
        assert not can_use_sql_rag(role)


def test_sql_gate_fails_closed_on_an_unknown_role():
    with pytest.raises(PermissionDenied):
        can_use_sql_rag("superuser")


# --- Refusal messages -------------------------------------------------------


def test_refusal_names_the_permitted_collections_and_not_the_restricted_ones():
    msg = refusal_message(Role.NURSE)
    assert "general" in msg and "nursing" in msg
    # Naming a restricted collection confirms it exists.
    for forbidden in ("billing", "clinical", "equipment"):
        assert forbidden not in msg


def test_refusal_is_not_a_generic_no_results_message():
    msg = refusal_message(Role.TECHNICIAN)
    assert "technician" in msg
    assert len(msg) > 100


def test_sql_refusal_explains_the_gate():
    msg = sql_refusal_message(Role.TECHNICIAN)
    assert "technician" in msg
    assert "admin" in msg and "billing executive" in msg


@pytest.mark.parametrize("role", list(Role))
def test_refusals_are_constructed_for_every_role(role: Role):
    assert refusal_message(role)
    assert sql_refusal_message(role)
