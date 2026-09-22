# SQL RAG — Worked Examples

Generated 2026-09-22 07:33 UTC by `uv run python scripts/sql_smoke.py`.

`sql_rag_chain(question)` is a plain Python function with three explicit steps:

1. `_generate_sql` — natural language to SQL, grounded in the real schema plus
   sampled distinct values per column, so the model uses `'escalated'` and not
   `'Escalated'`
2. `_extract_sql` — strip markdown fences, prose preamble and trailing
   explanation, then `_validate` — SELECT-only, single statement
3. `_execute` against a **read-only** connection, then `_summarize` the rows

Expected answers below were computed directly in SQL beforehand (see `data/DATA_NOTES.md` §4), so these outputs can be checked rather than
taken on trust.

Access is limited to `billing_executive` and `admin`.

## 1. How many claims were escalated in 2024?

*SQL shape:* COUNT with a WHERE filter

*Expected (computed independently):* 8

**Generated SQL**

```sql
SELECT COUNT(*) FROM claims WHERE status = 'escalated' AND submitted_date BETWEEN '2024-01-01' AND '2024-12-31'
```

**Rows returned:** 1

```
{'COUNT(*)': 8}
```

**Answer**

> There were **8** claims that were escalated in 2024.

## 2. Which equipment category has the most open maintenance tickets?

*SQL shape:* GROUP BY + ORDER BY + LIMIT

*Expected (computed independently):* radiology, with 4 tickets at status 'open' (note: under a looser 'not yet resolved' reading, monitoring and radiology tie at 11)

**Generated SQL**

```sql
SELECT category FROM maintenance_tickets WHERE status = 'open' GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1
```

**Rows returned:** 1

```
{'category': 'radiology'}
```

**Answer**

> The equipment category with the most open maintenance tickets is **radiology**.

## 3. What is the total claimed amount by department, highest first?

*SQL shape:* SUM + GROUP BY + ORDER BY

*Expected (computed independently):* orthopaedics 2,636,600 · cardiology 2,202,100 · nephrology 510,600 · gynaecology 397,600 · general_medicine 371,700 · neurology 342,700 · emergency 233,200

**Generated SQL**

```sql
SELECT department, SUM(claimed_amount) AS total_claimed_amount FROM claims GROUP BY department ORDER BY total_claimed_amount DESC
```

**Rows returned:** 7

```
{'department': 'orthopaedics', 'total_claimed_amount': 2636600.0}
{'department': 'cardiology', 'total_claimed_amount': 2202100.0}
{'department': 'nephrology', 'total_claimed_amount': 510600.0}
{'department': 'gynaecology', 'total_claimed_amount': 397600.0}
{'department': 'general_medicine', 'total_claimed_amount': 371700.0}
{'department': 'neurology', 'total_claimed_amount': 342700.0}
{'department': 'emergency', 'total_claimed_amount': 233200.0}
```

**Answer**

> - Orthopaedics: 2,636,600.0  
- Cardiology: 2,202,100.0  
- Nephrology: 510,600.0  
- Gynaecology: 397,600.0  
- General Medicine: 371,700.0  
- Neurology: 342,700.0  
- Emergency: 233,200.0

## 4. What percentage of claims are still pending?

*SQL shape:* Ratio over a filtered count

*Expected (computed independently):* 20.0% (17 of 85)

**Generated SQL**

```sql
SELECT ROUND(100.0 * SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pending_percentage FROM claims
```

**Rows returned:** 1

```
{'pending_percentage': 20.0}
```

**Answer**

> 20.0 % of the claims are still pending.

## 5. What is the average resolution time in days for maintenance tickets, by issue type?

*SQL shape:* Date arithmetic + GROUP BY, excluding NULLs

*Expected (computed independently):* battery_replacement 9.3 · sensor_failure 8.8 · fault_reported 8.0 · calibration_due 7.4 · preventive_maintenance 5.5 (42 resolved tickets)

**Generated SQL**

```sql
SELECT issue_type, AVG(julianday(resolved_date) - julianday(raised_date)) AS avg_resolution_days FROM maintenance_tickets WHERE resolved_date IS NOT NULL GROUP BY issue_type
```

**Rows returned:** 5

```
{'issue_type': 'battery_replacement', 'avg_resolution_days': 9.333333333333334}
{'issue_type': 'calibration_due', 'avg_resolution_days': 7.4}
{'issue_type': 'fault_reported', 'avg_resolution_days': 8.0}
{'issue_type': 'preventive_maintenance', 'avg_resolution_days': 5.5}
{'issue_type': 'sensor_failure', 'avg_resolution_days': 8.818181818181818}
```

**Answer**

> Here are the average resolution times (in days) for each issue type:

- **battery_replacement:** 9.33 days  
- **calibration_due:** 7.40 days  
- **fault_reported:** 8.00 days  
- **preventive_maintenance:** 5.50 days  
- **sensor_failure:** 8.82 days
