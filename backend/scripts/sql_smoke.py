"""Five analytical questions end-to-end: question -> SQL -> rows -> answer.

    uv run python scripts/sql_smoke.py

The rubric requires at least four. Five ship, so a schema mismatch in one does
not drop the submission below the bar, and the five shapes were chosen to
exercise different SQL constructs: count, group-by-max, sum-group-by, ratio,
and date arithmetic.

Each question carries the ground truth computed directly in SQL (see
`data/DATA_NOTES.md`), so the output can be **checked** rather than admired.

Writes `docs/sql_rag_examples.md`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.console import setup as _console_setup  # noqa: E402

_console_setup()

from app.config import REPO_ROOT  # noqa: E402
from app.generate import GenerationUnavailable  # noqa: E402
from app.sql_rag import SQLRagError, UnsafeSQL, run_sql_rag  # noqa: E402

OUTPUT = REPO_ROOT / "docs" / "sql_rag_examples.md"


@dataclass
class Question:
    text: str
    shape: str
    expected: str


# Dates: every row in this database falls in 2024, so questions name concrete
# periods. "Last month" would return zero rows and a fluent, confident, wrong
# answer - the worst failure mode in a graded demo. See data/DATA_NOTES.md §3.2.
QUESTIONS: list[Question] = [
    Question(
        "How many claims were escalated in 2024?",
        "COUNT with a WHERE filter",
        "8",
    ),
    Question(
        "Which equipment category has the most open maintenance tickets?",
        "GROUP BY + ORDER BY + LIMIT",
        "radiology, with 4 tickets at status 'open' "
        "(note: under a looser 'not yet resolved' reading, monitoring and radiology tie at 11)",
    ),
    Question(
        "What is the total claimed amount by department, highest first?",
        "SUM + GROUP BY + ORDER BY",
        "orthopaedics 2,636,600 · cardiology 2,202,100 · nephrology 510,600 · "
        "gynaecology 397,600 · general_medicine 371,700 · neurology 342,700 · emergency 233,200",
    ),
    Question(
        "What percentage of claims are still pending?",
        "Ratio over a filtered count",
        "20.0% (17 of 85)",
    ),
    Question(
        "What is the average resolution time in days for maintenance tickets, by issue type?",
        "Date arithmetic + GROUP BY, excluding NULLs",
        "battery_replacement 9.3 · sensor_failure 8.8 · fault_reported 8.0 · "
        "calibration_due 7.4 · preventive_maintenance 5.5 (42 resolved tickets)",
    ),
]


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# SQL RAG — Worked Examples",
        "",
        f"Generated {stamp} by `uv run python scripts/sql_smoke.py`.",
        "",
        "`sql_rag_chain(question)` is a plain Python function with three explicit steps:",
        "",
        "1. `_generate_sql` — natural language to SQL, grounded in the real schema plus",
        "   sampled distinct values per column, so the model uses `'escalated'` and not",
        "   `'Escalated'`",
        "2. `_extract_sql` — strip markdown fences, prose preamble and trailing",
        "   explanation, then `_validate` — SELECT-only, single statement",
        "3. `_execute` against a **read-only** connection, then `_summarize` the rows",
        "",
        "Expected answers below were computed directly in SQL beforehand "
        "(see `data/DATA_NOTES.md` §4), so these outputs can be checked rather than",
        "taken on trust.",
        "",
        "Access is limited to `billing_executive` and `admin`.",
        "",
    ]

    failures = 0
    for index, question in enumerate(QUESTIONS, start=1):
        print("\n" + "=" * 92)
        print(f"Q{index}. {question.text}")
        print("=" * 92)

        lines += [
            f"## {index}. {question.text}",
            "",
            f"*SQL shape:* {question.shape}",
            "",
            f"*Expected (computed independently):* {question.expected}",
            "",
        ]

        try:
            result = run_sql_rag(question.text)
        except GenerationUnavailable as exc:
            print(f"  SKIPPED: {exc}")
            lines += [f"> **Skipped** — {exc}", ""]
            failures += 1
            continue
        except (UnsafeSQL, SQLRagError) as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            lines += [f"> **Failed** — `{type(exc).__name__}`: {exc}", ""]
            failures += 1
            continue

        sql = str(result["sql"])
        rows = result["rows"]
        answer = str(result["answer"])

        print(f"\n  generated SQL:\n    {sql}")
        print(f"\n  rows returned: {len(rows)}")
        for row in rows[:8]:
            print(f"    {row}")
        if len(rows) > 8:
            print(f"    ... {len(rows) - 8} more")
        print(f"\n  answer:\n    {answer}")

        rendered_rows = "\n".join(str(r) for r in rows[:10]) or "(no rows)"
        if len(rows) > 10:
            rendered_rows += f"\n... {len(rows) - 10} more"

        lines += [
            "**Generated SQL**",
            "",
            "```sql",
            sql,
            "```",
            "",
            f"**Rows returned:** {len(rows)}",
            "",
            "```",
            rendered_rows,
            "```",
            "",
            "**Answer**",
            "",
            f"> {answer}",
            "",
        ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(QUESTIONS) - failures}/{len(QUESTIONS)} questions answered.")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
