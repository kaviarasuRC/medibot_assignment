# Dataset Notes

Recorded **before** any code was written, per `IMPLEMENTATION_PLAN.md` Phase 1.
Everything the SQL RAG prompt claims about value formats is verified here.

Source: `Medibot_Assignment_Resources.zip → mediassist_data.zip`.

---

## 1. Document corpus

12 files across the five collections. Every file is a PDF except one Markdown.

| Collection | File | Format | Size |
|---|---|---|---|
| `general` | `staff_handbook.pdf` | PDF | 99 KB |
| `general` | `leave_policy.pdf` | PDF | 94 KB |
| `general` | `code_of_conduct.pdf` | PDF | 94 KB |
| `general` | `general_faqs.pdf` | PDF | 94 KB |
| `clinical` | `treatment_protocols.pdf` | PDF | 106 KB |
| `clinical` | `drug_formulary.pdf` | PDF | 101 KB |
| `clinical` | `diagnostic_reference.pdf` | PDF | 99 KB |
| `nursing` | `icu_nursing_procedures.pdf` | PDF | 101 KB |
| `nursing` | `infection_control.pdf` | PDF | 97 KB |
| `billing` | `billing_codes.pdf` | PDF | 100 KB |
| `billing` | `claim_submission_guide.md` | **Markdown** | 13 KB |
| `equipment` | `equipment_manual.pdf` | PDF | 104 KB |

Two consequences for ingestion:

- **11 of 12 files need the Docling PDF pipeline**, which downloads layout +
  TableFormer models on first run. Pre-download with `docling-tools models download`.
- `claim_submission_guide.md` is pure Python to parse (no models). It is a useful
  smoke test for the chunking code before paying the PDF model cost.

The collection folder name is authoritative — `collection_map.py` derives the
collection from it and raises on anything unmapped rather than defaulting to
`general`.

---

## 2. `mediassist.db`

SQLite, 48 KB, two tables. Opened **read-only** at runtime
(`file:...?mode=ro`, `uri=True`).

### 2.1 `claims` — 85 rows

```sql
CREATE TABLE claims (
    claim_id        TEXT PRIMARY KEY,   -- 'CLM-2024-1000' .. 'CLM-2024-1084'
    patient_id      TEXT,               -- 'PAT-10942' .. 'PAT-99353'
    patient_name    TEXT,
    department      TEXT,
    claim_type      TEXT,
    diagnosis_code  TEXT,               -- ICD-10, e.g. 'N17.9', 'I21.4', 'A09'
    insurer         TEXT,
    claimed_amount  REAL,               -- 4000.0 .. 228900.0
    approved_amount REAL,               -- NULL for 41 of 85 rows
    status          TEXT,
    submitted_date  TEXT,               -- 'YYYY-MM-DD'
    resolved_date   TEXT                -- 'YYYY-MM-DD', NULL for 29 of 85 rows
)
```

| Column | Exact values (lowercase, verified) |
|---|---|
| `status` | `pending` (17), `approved` (44), `rejected` (12), `submitted` (4), `escalated` (8) |
| `claim_type` | `cashless` (60), `reimbursement` (25) |
| `department` | `cardiology`, `orthopaedics`, `general_medicine`, `gynaecology`, `nephrology`, `neurology`, `emergency` |
| `insurer` | `New India Assurance`, `Bajaj Allianz`, `United India`, `HDFC Ergo`, `Star Health`, `Care Health`, `ICICI Lombard`, `Niva Bupa` — **Title Case, unlike every other enum** |

### 2.2 `maintenance_tickets` — 78 rows

```sql
CREATE TABLE maintenance_tickets (
    ticket_id       TEXT PRIMARY KEY,   -- 'TKT-2024-2000' .. 'TKT-2024-2077'
    equipment_name  TEXT,
    equipment_id    TEXT,               -- 'EQ-<campus>-<4 digits>'
    category        TEXT,
    campus          TEXT,
    issue_type      TEXT,
    fault_code      TEXT,               -- NULL for 30 of 78 rows
    raised_by       TEXT,
    raised_date     TEXT,               -- 'YYYY-MM-DD'
    resolved_date   TEXT,               -- NULL for 36 of 78 rows
    status          TEXT,
    resolution_note TEXT                -- NULL for 36 of 78 rows
)
```

| Column | Exact values (lowercase, verified) |
|---|---|
| `status` | `resolved` (42), `in_progress` (15), `open` (11), `escalated` (10) |
| `category` | `monitoring` (25), `infusion` (19), `radiology` (13), `sterilisation` (12), `surgical` (6), `laboratory` (3) |
| `issue_type` | `sensor_failure` (22), `preventive_maintenance` (18), `fault_reported` (14), `calibration_due` (13), `battery_replacement` (11) |
| `equipment_name` | `SterilPro 3000`, `DriveFlow IP-200`, `RadiPro MX-150`, `BM-500 Monitor`, `ElectroCautery EC-90`, `HemaCount HC-20` |
| `campus` | `MediAssist Hyderabad Central`, `MediAssist Bengaluru Onco Centre`, `MediAssist Pune Speciality`, `MediAssist Secunderabad`, `MediAssist Mysuru Clinic Hub` |

---

## 3. Three findings that change the implementation

### 3.1 Enum values are lowercase `snake_case`, not Title Case

`DESIGN.md` §8.2 warns that if `status` is `'Escalated'` and the model emits
`'escalated'` you get zero rows and a confidently wrong answer. The warning is
right; the direction is backwards. **Every enum-like value in this database is
lowercase**, and multi-word values use underscores (`in_progress`,
`preventive_maintenance`, `general_medicine`).

The one exception is `claims.insurer`, which is Title Case with spaces
(`New India Assurance`). A prompt that says "values are lowercase" would be
wrong for that column, so the SQL prompt ships **sampled distinct values per
column**, not a blanket rule about casing.

### 3.2 All dates fall in 2024; "last month" returns zero rows

`claims.submitted_date` spans `2024-01-03` → `2024-12-19`.
`maintenance_tickets.raised_date` spans `2024-01-08` → `2024-12-28`.

Today is well past that window, so the planned demo question *"how many billing
claims were escalated last month?"* is a guaranteed empty result — a fluent,
confident, wrong answer, which is the worst failure mode in a graded demo.

**Resolution:** demo questions name concrete 2024 periods. The SQL generation
prompt also states the available date range explicitly, so a user who does ask a
relative-date question gets a query scoped to real data rather than to a range
the table has never contained.

Escalated claims by month, for reference: `2024-01` (1), `2024-03` (1),
`2024-05` (2), `2024-08` (3), `2024-10` (1). Total **8**. None in Nov or Dec.

### 3.3 "Most open tickets" is ambiguous — and the two readings disagree

| Reading | Winner |
|---|---|
| `status = 'open'` strictly | **radiology, 4** (then monitoring 3, infusion 2) |
| "not yet resolved" (`open` + `in_progress` + `escalated`) | **monitoring 11 and radiology 11 — a tie** |

Because the loose reading ties, the demo question is phrased to target the
literal `open` status, and the expected answer is recorded as radiology. Noted
here so a differing answer is recognised as a routing/prompt change rather than
a regression.

---

## 4. Expected answers for the demo questions

Ground truth computed directly in SQL, so `scripts/sql_smoke.py` output can be
checked rather than admired.

| # | Question | Expected |
|---|---|---|
| 1 | How many claims were escalated in 2024? | **8** |
| 2 | Which equipment category has the most open maintenance tickets? | **radiology (4)** |
| 3 | What is the total claimed amount by department, highest first? | orthopaedics ₹2,636,600 · cardiology ₹2,202,100 · nephrology ₹510,600 · gynaecology ₹397,600 · general_medicine ₹371,700 · neurology ₹342,700 · emergency ₹233,200 |
| 4 | What percentage of claims are still pending? | **20.0%** (17 of 85) |
| 5 | What is the average resolution time for maintenance tickets by issue type? | battery_replacement 9.3d · sensor_failure 8.8d · fault_reported 8.0d · calibration_due 7.4d · preventive_maintenance 5.5d (42 resolved tickets; 36 have a NULL `resolved_date` and are excluded) |

Question 5 is the one most likely to go wrong: a model that forgets
`WHERE resolved_date IS NOT NULL` silently averages over NULLs. SQLite's
`AVG` skips NULL operands, so the result happens to come out right — but the
row **count** would be wrong in any query that also reports one.
