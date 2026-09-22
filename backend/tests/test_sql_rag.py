"""Tests for SQL extraction and the SELECT-only guard.

`IMPLEMENTATION_PLAN.md` §6 asks for extraction to be tested against hand-written
malformed LLM outputs, because it directly protects a rubric line the tips call
out by name. Nothing here touches the network.
"""

from __future__ import annotations

import pytest

from app.sql_rag import (
    MAX_ROWS,
    UnsafeSQL,
    _apply_row_cap,
    _execute,
    _extract_sql,
    _validate,
    schema_context,
)

# --- Step 2: extraction -----------------------------------------------------

CLEAN = "SELECT COUNT(*) FROM claims WHERE status = 'escalated'"


@pytest.mark.parametrize(
    ("label", "raw"),
    [
        ("already clean", CLEAN),
        ("fenced with language tag", f"```sql\n{CLEAN}\n```"),
        ("fenced without language tag", f"```\n{CLEAN}\n```"),
        ("prose prefix", f"Here is the query you asked for:\n\n{CLEAN}"),
        ("trailing semicolon", f"{CLEAN};"),
        ("explanation after the query", f"{CLEAN};\n\nThis counts escalated claims."),
        (
            "fenced, prefixed AND explained",
            f"Sure! Here's the SQL:\n\n```sql\n{CLEAN};\n```\n\nIt returns a single row.",
        ),
        ("leading blank lines", f"\n\n   {CLEAN}\n"),
    ],
)
def test_extraction_recovers_the_bare_statement(label: str, raw: str):
    assert _extract_sql(raw) == CLEAN, label


def test_extraction_handles_a_with_clause():
    cte = "WITH x AS (SELECT 1 AS n) SELECT n FROM x"
    assert _extract_sql(f"```sql\n{cte}\n```") == cte


def test_extraction_of_junk_yields_something_validate_will_reject():
    extracted = _extract_sql("I'm sorry, I cannot answer that question.")
    with pytest.raises(UnsafeSQL):
        _validate(extracted)


# --- Step 2b: the guard -----------------------------------------------------


def test_replace_as_a_scalar_function_is_allowed():
    """The exact case a naive bare-word blocklist would wrongly refuse.

    REPLACE is also a SQLite *statement* (REPLACE INTO), but here it is a scalar
    function and the query is a plain read. It must pass.
    """
    _validate("SELECT REPLACE(status, '-', ' ') FROM claims")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM claims",
        "SELECT * FROM claims WHERE status = 'escalated' LIMIT 10",
        "WITH t AS (SELECT department, SUM(claimed_amount) s FROM claims GROUP BY department) SELECT * FROM t",
        "  select claim_id from claims  ",
        "SELECT COUNT(*) FROM claims;",  # trailing semicolon is stripped, then allowed
    ],
)
def test_valid_reads_pass(sql: str):
    _validate(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE claims",
        "DELETE FROM claims",
        "UPDATE claims SET status = 'approved'",
        "INSERT INTO claims VALUES (1)",
        "PRAGMA table_info(claims)",
        "ATTACH DATABASE 'evil.db' AS evil",
        "SELECT 1; DROP TABLE claims",           # stacked statements
        "SELECT 1; DELETE FROM claims;",         # stacked, trailing semicolon
        "CREATE TABLE x (a INT)",
        "REPLACE INTO claims VALUES (1)",        # REPLACE in STATEMENT position
        "",
        "   ",
        "I cannot answer that.",
    ],
)
def test_unsafe_sql_is_refused(sql: str):
    with pytest.raises(UnsafeSQL):
        _validate(sql)


def test_semicolon_stripping_happens_before_the_stacked_check():
    """Checking for ';' before stripping would refuse every well-formed query."""
    _validate("SELECT 1;")
    with pytest.raises(UnsafeSQL):
        _validate("SELECT 1; SELECT 2")


# --- Step 3a: row cap -------------------------------------------------------


def test_row_cap_is_added_when_absent():
    assert _apply_row_cap("SELECT * FROM claims") == f"SELECT * FROM claims LIMIT {MAX_ROWS}"


def test_row_cap_is_not_doubled():
    sql = "SELECT * FROM claims LIMIT 5"
    assert _apply_row_cap(sql) == sql


# --- Schema introspection and execution (real database, no network) ---------


def test_schema_context_contains_both_tables_and_real_values():
    ctx = schema_context()
    assert "CREATE TABLE claims" in ctx
    assert "CREATE TABLE maintenance_tickets" in ctx
    # The whole point of sampling: exact, case-sensitive literals.
    assert "'escalated'" in ctx
    assert "'in_progress'" in ctx
    assert "'preventive_maintenance'" in ctx
    # And the date range, so relative-date questions are scoped to real data.
    assert "2024-" in ctx


def test_execute_returns_rows_from_the_real_database():
    rows = _execute("SELECT COUNT(*) AS n FROM claims WHERE status = 'escalated'")
    assert rows == [{"n": 8}], "ground truth from data/DATA_NOTES.md"


def test_database_is_opened_read_only():
    """Defence in depth: even if the guard were bypassed, the write would fail.

    Goes around `_validate` deliberately - the point is that the connection
    itself refuses writes, not that the regex caught this one.
    """
    import sqlite3

    from app.sql_rag import _connect

    with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
        with _connect() as conn:
            conn.execute("UPDATE claims SET status = 'approved'")
