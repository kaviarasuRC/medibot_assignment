# MediBot — Implementation Plan

**Companion to:** `DESIGN.md`
**Target:** public GitHub repo, backend + frontend, README with adversarial evidence
**Estimated effort:** ~26.5 hours across 10 phases (0–9). Rubric-complete without the frontend: ~22.5 h.

---

## 0. Ground Rules

- **Build the pipeline bottom-up and headless.** Phases 1–6 are pure Python with no FastAPI and no React — you can run and verify every one of them from a script. The API in Phase 7 is a thin wrapper over a pipeline that is already proven, which is exactly the argument that RBAC lives in retrieval rather than in the web layer.
- **RBAC is not a phase.** It is designed into Phase 2 (ingestion writes the labels) and Phase 4 (retrieval applies the filter). Phase 5 only *proves* it. Do not plan to "add access control later" — retrofitting it is how leaks happen.
- Each phase ends in a committed, runnable state.
- Type-hint everything as you write it. 5% of the grade, free if you don't defer it.

### Three silent failures — tape these to your monitor

All three were verified against the current libraries. None of them raise. None of them warn.

1. `HybridChunker(max_tokens=512)` is **ignored** when you pass a real `BaseTokenizer`. Set `max_tokens` on the **tokenizer**.
2. `repeat_table_headers` (plural) is **swallowed** by pydantic. The field is `repeat_table_header` (singular).
3. The cross-encoder is now `cross-encoder/ms-marco-MiniLM-L6-v2`. The `L-6-v2` spelling all over the internet is legacy.

---

## Phase 0 — Environment (1.5 h)

### Tasks

1. Public GitHub repo `medibot`, Python + Node `.gitignore`.
2. ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install fastapi "uvicorn[standard]" qdrant-client fastembed \
               "docling-core[chunking]" docling "sentence-transformers>=5" torch \
               transformers groq python-dotenv pydantic pydantic-settings \
               "python-jose[cryptography]" pytest httpx
   pip freeze > requirements.txt
   ```
   `sentence-transformers>=5` is pinned because the `CrossEncoder` kwargs changed in v5. `transformers` is listed explicitly — `AutoTokenizer` is imported directly in Phase 2, so relying on it arriving transitively is fragile. No `passlib`: the demo user store uses `secrets.compare_digest`, and shipping an unused auth dependency implies a design the code doesn't have.
3. `docker-compose.yml`:
   ```yaml
   services:
     qdrant:
       image: qdrant/qdrant:latest
       ports: ["6333:6333", "6334:6334"]
       volumes: ["./qdrant_storage:/qdrant/storage"]
   ```
   `docker compose up -d`, confirm the dashboard at `http://localhost:6333/dashboard`.
4. **Pre-download Docling models now, not on demo day:**
   ```bash
   docling-tools models download   # → ~/.cache/docling/models
   ```
   Hundreds of MB. Only needed for PDF/image pipelines; Markdown is pure Python.
5. `.env` (gitignored) + `.env.example` (committed):
   ```
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION=medibot_documents
   SQLITE_PATH=./data/mediassist.db
   JWT_SECRET=change-me
   EMBED_MODEL=BAAI/bge-small-en-v1.5
   SPARSE_MODEL=Qdrant/bm25
   RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2
   ```
   And `frontend/.env.local` (plus `.env.local.example`, committed):
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   Easy to forget, and without it the Phase 9 "fresh clone works first try" check fails.
6. Drop the provided dataset into `data/documents/{general,clinical,nursing,billing,equipment}/` and `data/mediassist.db`.
7. `git log --all --full-history -- .env` must return nothing before you push.

**Commit:** `chore: scaffold backend, Qdrant compose, and dependencies`

---

## Phase 1 — Inspect the data before writing any code (1 h)

Skipping this phase is the most expensive mistake available to you. The assignment says so explicitly, twice.

### Tasks

1. **Schema and value formats:**
   ```bash
   sqlite3 data/mediassist.db ".schema"
   sqlite3 data/mediassist.db "SELECT * FROM claims LIMIT 5;"
   sqlite3 data/mediassist.db "SELECT DISTINCT status FROM claims;"
   sqlite3 data/mediassist.db "SELECT DISTINCT category FROM maintenance_tickets;"
   sqlite3 data/mediassist.db "SELECT DISTINCT status FROM maintenance_tickets;"
   ```
   Write down the **exact casing** of every enum-like value and the **date format**. If `status` is `'Escalated'` and your LLM emits `'escalated'`, SQLite returns zero rows and you ship a confidently wrong answer.
2. **Date range:** `SELECT MIN(date_col), MAX(date_col) FROM claims;` — "last month" is meaningless if the data ends in 2024. You may need to phrase demo questions relative to the actual range.
3. **Document inventory:** list every file per collection folder, note which are PDF vs Markdown, and open the two most table-heavy PDFs to see what you're asking Docling to parse.
4. Record all of it in `data/DATA_NOTES.md` (committed). This becomes source material for the README.

**Commit:** `docs: dataset inventory and schema notes`

---

## Phase 2 — Ingestion (4 h)

### 2.1 `app/rbac.py` first

Write the access matrix **before** the ingestion script, because ingestion imports from it. This is what guarantees the labels written at index time and the filter applied at query time can never disagree.

```python
ROLE_COLLECTIONS: dict[Role, frozenset[Collection]]
def roles_for_collection(c: Collection) -> list[str]
def rbac_filter(role: Role) -> models.Filter
def collections_for_role(role: Role) -> list[str]
SQL_RAG_ROLES: frozenset[Role]
```

Tests before moving on: every collection is reachable by at least one role; `admin` reaches all five; `nurse` does not reach `billing` or `equipment`; an unknown role raises rather than returning an empty filter.

> An empty `models.Filter()` matches **everything**. A fail-open bug here is the whole assignment lost. Make the unknown-role path raise, and test it.

### 2.2 `ingest/collection_map.py`

`collection_for_path(p) -> Collection`, folder-based, **raising `UnmappedDocument` on anything unrecognised.** Never default to `general` — that would silently publish a restricted document to every role.

### 2.3 `ingest/chunking.py`

```python
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5"),
    max_tokens=512,                     # ← on the TOKENIZER, not the chunker
)
chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)
```

Add a startup assertion: `assert chunker.max_tokens == 512` — this is the only thing that catches silent failure #1.

Implement `chunk_type(chunk)` per DESIGN §5.5, iterating all `doc_items` (merge_peers can put several in one chunk) and letting `table`/`code` win over incidental text.

### 2.4 `ingest/parse.py` and `ingest/ingest.py`

`parse.py` is a thin wrapper — `to_docling_document(path) -> DoclingDocument` — holding one shared `DocumentConverter` (it is expensive to construct) plus the `artifacts_path` override for pre-downloaded models. Separating it keeps `ingest.py` about orchestration.

Order of operations per document:

0. Delete any existing points for this `source_document` (DESIGN §5.8) — deterministic IDs alone leave orphans behind when a document shrinks
1. `to_docling_document(path)`
2. `chunker.chunk(dl_doc=doc)`
3. Per chunk: `embed_text = chunker.contextualize(chunk=chunk)`, `display_text = chunk.text`
4. Dense: `next(dense_model.embed([embed_text])).tolist()` — note `embed()`, not `query_embed()`, for documents
5. Sparse: `next(sparse_model.embed([embed_text]))` → `.indices.tolist()`, `.values.tolist()`
6. Payload per DESIGN §5.5, with `access_roles = roles_for_collection(collection)`
7. Deterministic point ID: `uuid5(NAMESPACE_URL, f"{source_document}:{chunk_index}")`
8. Batch upsert, 64 points at a time

Collection creation with `Modifier.IDF` and both payload indexes per DESIGN §6.1. `--recreate` flag drops and rebuilds.

### 2.5 Verify before moving on

```bash
python -m ingest.ingest --recreate
```

Then a throwaway script that prints, for 5 random points: the `section_title`, the first 200 chars of the embedded text, `chunk_type`, and `access_roles`.

**Read that output with your own eyes.** Specifically check:
- Does the embedded text actually start with headings? (proves `contextualize()` worked)
- Do table chunks look like coherent tables, not fragments?
- Does `access_roles` on a `billing` chunk read `["admin", "billing_executive"]` and nothing else?

Also, two idempotency checks — the second is the one people skip:

1. Run ingestion twice; the point count must not double.
2. Truncate a copy of one document to half its length, re-ingest just that file, and confirm the high-index chunks from the first run are **gone**. Deterministic IDs overwrite but never delete, so without the step-0 filter delete those orphans stay live and answer questions with stale text — and the point count won't tell you.

**Commit:** `feat: Docling ingestion with hierarchical chunking and RBAC metadata`

---

## Phase 3 — Retrieval (3 h)

### 3.1 `app/embeddings.py`

Module-level singletons. Loading FastEmbed per request costs seconds.

```python
dense_model  = TextEmbedding(settings.embed_model)
sparse_model = SparseTextEmbedding(settings.sparse_model)
```

### 3.2 `app/retrieval.py`

`hybrid_search(question, role, limit=20)` exactly as DESIGN §6.3. The one thing to get right: **`query_filter` at the top level, not inside each `Prefetch`.** It propagates into both branches as a pre-filter. Per-prefetch filters are AND-merged with it, so repeating it is harmless but redundant — one place means one thing to get wrong.

Use `query_embed()` here, not `embed()`. For BM25 this changes the output (no document-length normalization) and it's the correct asymmetry.

### 3.3 Prove the filter before trusting it

Before writing another line, run this by hand:

```python
for role in Role:
    pts = hybrid_search("insurance billing code for cardiac procedures", role, limit=20)
    print(role.value, sorted({p.payload["collection"] for p in pts}))
```

Expected:
```
doctor             ['clinical', 'general', 'nursing']
nurse              ['general', 'nursing']
billing_executive  ['billing', 'general']
technician         ['equipment', 'general']
admin              ['billing', 'clinical', 'equipment', 'general', 'nursing']
```

If any row shows a collection outside the matrix, stop and fix it. Everything downstream is worthless until this table is correct.

### 3.4 `scripts/compare_retrieval.py`

Three configurations (dense-only, hybrid, hybrid+rerank) × the five probe queries from DESIGN §6.4. Prints top-3 per configuration. Save the output to `docs/retrieval_comparison.md` — this is the 20% evidence.

**Give it a pass criterion, not just a table.** "Demonstrably better" needs a number a reviewer can read without domain knowledge. After running the probes once, hand-label the single chunk that *should* rank first for each query (you'll recognise it immediately), record it as `expected_source_document` + a substring, and report **hit@3 per configuration**:

```
                   hit@3
dense only          2/5     misses: ICD-10 A41.9, Fresenius 4008S
hybrid              5/5
hybrid + rerank     5/5     (mean rank of the correct chunk: 2.4 → 1.2)
```

Five hand-labels is fifteen minutes of work and converts a table someone must squint at into a claim that defends itself.

Run it *after* Phase 4 so the rerank column is populated, but write it now.

**Commit:** `feat: hybrid dense+BM25 retrieval with RBAC pre-filter`

---

## Phase 4 — Reranking and answer generation (2.5 h)

### 4.1 `app/config.py`

Pydantic-settings over the `.env` from Phase 0: model IDs, Qdrant URL, collection name, top-k values, SQLite path, JWT secret. Everything else imports settings from here — no `os.getenv` scattered through the codebase.

### 4.2 `app/rerank.py`

```python
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L6-v2",
    activation_fn=torch.nn.Sigmoid(),
    max_seq_length=512,
    device="cpu",
)
```

Pin `sentence-transformers>=5` — in 4.x the kwarg was `default_activation_function` and `max_seq_length` was `max_length`, so this snippet is a `TypeError` on an older install. Sigmoid is already the default for these models (`num_labels == 1`), but passing it explicitly documents the 0–1 range at the call site and survives a model swap.

`rerank(question, candidates, top_k=3) -> list[tuple[float, Chunk]]`.

Behind `MEDIBOT_LOG_RERANK=1`, log a table per query:

```
hybrid_rank  rerank_score  new_rank  section_title
    1           0.0412        4       Leave Policy > Carry Forward
    4           0.9871        1       Claim Rejection Codes > Escalation
```

**Capture one of these where the ordering genuinely changes and put it in the README.** It is the single most persuasive artifact for this component — it shows reranking doing work rather than claiming it does.

Tests: reranker returns exactly `top_k`; scores are in [0,1] (proves the sigmoid is applied); an empty candidate list returns empty rather than raising.

### 4.3 `app/generate.py`

The document-answer step. It is built here, not in Phase 7, because Phase 5's adversarial cases need to assert on refusals and Phase 3's comparison harness reads better with real answers.

```python
def generate_answer(question: str, role: Role,
                    chunks: list[tuple[float, Chunk]]) -> tuple[str, list[Source]]
```

- The five-rule system prompt from DESIGN §10.1. Rule 5 — *never comment on what other roles can access* — is the one people omit and then watch the model helpfully name the billing handbook it can't see.
- Context block numbered `[1] [2] [3]` with `source_document` and `section_title` on each, so the citation format the model is asked for is the format it can see.
- Temperature `0.1`. This is extraction, not composition.
- **Empty chunk list → return `refusal_message(role)` and never call the LLM.** Cheaper, faster, and it makes the refusal text deterministic and therefore assertable.
- `sources` is built from the chunks actually passed in, not parsed out of the model's prose.

Test with a hand-built 3-chunk fixture and no network, asserting the prompt contains all three sources and the role.

**Commit:** `feat: cross-encoder reranking, citation-grounded generation, settings`

---

## Phase 5 — The adversarial suite (2 h — do this before the API)

Building this *before* FastAPI is deliberate. It tests the pipeline where the security actually lives, so a passing suite here means the API can only weaken things, never be the sole line of defence.

### `scripts/adversarial_test.py`

Implement the 7 cases from DESIGN §4.5. Assert on **retrieved chunk collections**, not answer text:

```python
@dataclass
class AdversarialCase:
    name: str
    role: Role
    question: str
    forbidden_collections: set[str]
    expect_refusal: bool = False
    requires: str | None = None      # None | "api" — see the table below

def run(case) -> Result:
    pts = hybrid_search(case.question, case.role, limit=20)
    got = {p.payload["collection"] for p in pts}
    leaked = got & case.forbidden_collections
    passed = not leaked
    if case.expect_refusal:
        answer, _ = generate_answer(case.question, case.role, rerank(case.question, pts))
        passed = passed and answer == refusal_message(case.role)
    return Result(passed=passed, retrieved=sorted(got), leaked=sorted(leaked))
```

Asserting on the answer text only proves the model behaved *this time*. Asserting on retrieval proves it *cannot* misbehave.

Output a markdown table to `docs/adversarial_results.md`. That file plus terminal screenshots is the 25% deliverable.

### Which cases run when

Not all seven are runnable at this point, and the split is deliberate — the five that matter most are provable *before* any HTTP layer exists, which is the whole argument that RBAC lives in retrieval rather than in the API.

| Case | Assertion | Runs in |
|---|---|---|
| 1, 2, 4, 5 | No forbidden collection retrieved | **Phase 5** — pure retrieval |
| 3 | No clinical chunk **and** a refusal returned | **Phase 5** — needs `generate.py` from Phase 4, which is why generation moved earlier |
| 6 | Body `role` ignored; token role wins | Phase 7 — needs the API |
| 7 | SQL gate refuses a technician | Phase 7 — needs `router.py` + the gate |

Build the harness so cases carry an optional `requires` marker and skip cleanly with `SKIPPED (needs API)` rather than failing. Phase 7 flips them on and the suite runs 7/7.

**Commit:** `test: adversarial RBAC suite with retrieval-level assertions`

---

## Phase 6 — SQL RAG (3 h)

### `app/sql_rag.py`

Write it as the literal three-step plain function from DESIGN §8.1. Not a LangChain chain — the rubric says "plain Python function" and a reviewer will look.

Build order:

1. **Schema introspection** at import: `SELECT sql FROM sqlite_master WHERE type='table'`, plus 3 sample rows per table into `SCHEMA_CONTEXT`. Use the value formats you recorded in Phase 1.
2. **Read-only connection:** `sqlite3.connect("file:...?mode=ro", uri=True)`.
3. `_generate_sql` — Groq, temperature 0, "SQLite dialect, SELECT only, bare query, no prose, no fences."
4. `_extract_sql` — fence stripping + slice from first `SELECT`/`WITH` (DESIGN §8.3). Note that `sql_rag_chain` calls `_validate` between extraction and execution — DESIGN §8.1 shows the full four-call shape. **Unit-test extraction against 6 hand-written malformed LLM outputs** — fenced, prose-prefixed, trailing semicolon, `sql` language tag, explanation after the query, and a clean query. It's 20 lines of test that directly protects a rubric line the tips call out by name.
5. `_validate` — SELECT-only guard, no stacked statements, forbidden keywords **matched in statement position only**. A bare-word blocklist rejects `SELECT REPLACE(status,'-',' ') FROM claims`, since `REPLACE` is also a SQLite scalar function. Add that exact string as a test case that must *pass* validation.
6. `_execute` — with `LIMIT 200` injected if absent.
7. `_summarize` — rows + original question + executed SQL → natural language.

Every step wrapped so a failure returns a friendly message rather than a traceback.

### `scripts/sql_smoke.py`

The 5 questions from DESIGN §8.7. Print question → generated SQL → rows → answer for each. Save to `docs/sql_rag_examples.md` — the 15% evidence.

**Commit:** `feat: three-step SQL RAG with extraction and SELECT-only guard`

---

## Phase 7 — FastAPI (3 h)

### Build order

1. `app/models.py` — request/response schemas per DESIGN §10.3. **`ChatRequest` has no `role` field and uses `extra="ignore"`**, so a client sending one is silently downgraded rather than handed a 422 that reveals which field the server cares about.
2. `app/auth.py` — 5 demo users, `secrets.compare_digest`, JWT with `sub` + `role`, 8h expiry. `get_current_role()` dependency.
3. `app/router.py` — the two-cue analytical classifier (DESIGN §9).
4. `app/rag_pipeline.py` — `retrieve → assert → rerank → generate`, returning the response model. The layer-3 assertion lives here:
   ```python
   allowed = {c.value for c in ROLE_COLLECTIONS[role]}
   for p in points:
       if p.payload["collection"] not in allowed:
           log.critical("RBAC LEAK role=%s collection=%s", role, p.payload["collection"])
           raise RBACViolation
   ```
5. `app/routes/*.py` — the four endpoints.
6. `app/main.py` — CORS restricted to `http://localhost:3000`, models warmed at startup so the first request isn't 30 seconds. Run with `uvicorn app.main:app --reload`.
7. Flip on adversarial cases 6 and 7 and re-run the suite — it should now report **7/7**, and that output is what goes in the README.

### Critical detail

**`/chat` must ignore any `role` in the request body.** Take it only from `get_current_role()`. If you accept a body role "for convenience", you have built a UI-level control and lost the 25%.

### Tests

`tests/test_api.py` with `httpx.AsyncClient`:

- login with each of the 5 users returns the right role
- `/chat` without a token → 401
- `/chat` with a nurse token but `"role": "admin"` in the body → response `role` is `nurse` **(this completes adversarial case 6)**
- `/collections/nurse` returns exactly `["general", "nursing"]`
- technician asking an analytical question → refusal, `retrieval_type` not `sql_rag`
- every successful response contains a `sources` key

**Commit:** `feat: FastAPI backend with token-derived RBAC and source citations`

---

## Phase 8 — Next.js frontend (4 h)

```bash
npx create-next-app@latest frontend --typescript --tailwind --app
```

### Build order

1. `lib/api.ts` — typed fetch wrapper, token in `localStorage`, 401 → redirect to login.
2. `app/page.tsx` — login. **Five buttons that prefill each demo credential pair.** A reviewer switching roles in one click will exercise your RBAC far more than one who has to type.
3. `app/chat/page.tsx` — layout with sidebar.
4. `RoleBadge` — colour per role, always visible in the header.
5. `CollectionChips` — from `/collections/{role}`, sidebar.
6. `MessageBubble` — answer + retrieval-type pill.
7. `SourceCitation` — one card per source: document name, section path, collection tag.
8. Refusal rendering — amber background, lock icon, visually distinct from both a normal answer and an error.

### Manual matrix

| # | Action | Expected |
|---|---|---|
| 1 | Login as each of 5 users | Correct role badge, correct chips |
| 2 | Nurse: "what is the hand hygiene protocol in ICU?" | Answer with nursing citations |
| 3 | Nurse: "show me all insurance billing codes" | Amber refusal naming general + nursing |
| 4 | Billing: same question | Real answer with billing citations |
| 5 | Billing: "how many claims were escalated last month?" | `SQL RAG` pill, SQL shown |
| 6 | Technician: same question | Refusal — role lacks SQL access |
| 7 | Admin: any question | Works across all collections |
| 8 | Kill the backend, ask a question | Friendly error, not a blank screen |

Rows 3 and 4 back to back are your best screenshot — same question, two roles, two outcomes.

**Commit:** `feat: Next.js chat UI with role badge, citations, and RBAC refusals`

---

## Phase 9 — README & submission (2.5 h)

The README is directly graded (part of the 5%) and is where the 25% RBAC evidence lives. Budget real time for it.

### Structure

```markdown
# MediBot — Advanced RAG with Role-Based Access Control

Screenshot: same question, nurse vs billing_executive, side by side.

## What this is
2 paragraphs — problem, and the one-line thesis:
"RBAC is enforced as a Qdrant metadata pre-filter, so the LLM never sees a
restricted chunk and therefore cannot leak one."

## Architecture
Diagram (from DESIGN §3.1) + the query-flow diagram:
login → token → role → RBAC filter → hybrid retrieval → rerank → LLM → cited answer

## Setup
docker compose up -d
pip install -r requirements.txt
docling-tools models download        ← call this out, it's slow
cp .env.example .env  (add GROQ_API_KEY)
python -m ingest.ingest --recreate
uvicorn app.main:app --reload
cd frontend && cp .env.local.example .env.local && npm install && npm run dev

## Demo credentials
Table of all 5 users, passwords, roles, and accessible collections.

## RBAC: how it's enforced      ← the 25%
- The access matrix
- The exact query_filter code block
- Why MatchValue (contains) and not MatchAny (permissive OR)
- The 5 defence layers
- ADVERSARIAL TESTS — 7 cases, table of results, screenshots
- How to reproduce: python scripts/adversarial_test.py

## Retrieval quality           ← the 20%
- Dense vs hybrid vs hybrid+rerank on 5 probe queries
- The reranker log showing rank 4 → rank 1
- Why Modifier.IDF is required for BM25

## Chunking                    ← the 20%
- contextualize() output example (before/after)
- The metadata schema table
- Why tables serialize as triplets

## SQL RAG                     ← the 15%
- The three steps
- 5 worked examples: question → SQL → answer

## Tool substitutions and decisions
- Groq + gpt-oss-120b (Llama line deprecated 16 Aug 2026)
- RRF over DBSF, and why
- doctor's access to `nursing` — reading of the spec
- One Qdrant collection + payload field vs physical separation

## Project structure
## Running the tests
```

### Final checklist

- [ ] `.env` never committed — `git log --all --full-history -- .env` is empty
- [ ] Repo is **public**
- [ ] Fresh clone → setup steps → works first try (test this literally, in a new directory)
- [ ] `pytest` green
- [ ] `scripts/adversarial_test.py` — **7/7 pass** (not 5/7 with two skipped), output committed
- [ ] `frontend/.env.local.example` committed with `NEXT_PUBLIC_API_URL`
- [ ] Re-ingesting a shortened document leaves no orphan chunks
- [ ] `scripts/compare_retrieval.py` output committed
- [ ] `scripts/sql_smoke.py` output committed
- [ ] ≥3 adversarial screenshots embedded in the README
- [ ] Architecture diagram in the README
- [ ] All 5 demo credentials documented and working
- [ ] Every `/chat` response contains `sources`
- [ ] No `print()` debugging; `logging` throughout

**Commit:** `docs: README with architecture, adversarial evidence, and setup`

---

## Rubric Coverage by Phase

| Criterion | Weight | Phases |
|---|---|---|
| RBAC at retrieval layer + 3 adversarial attempts | 25% | 2 (matrix + labels), 3 (filter), **5 (proof, cases 1–5)**, 7 (token-derived role, cases 6–7), 9 (documented) |
| Structural parsing + hierarchical chunking + metadata | 20% | 2 |
| Hybrid RAG better than dense-only | 20% | 3, 4, and `compare_retrieval.py` with hit@3 |
| SQL RAG plain function, 4+ questions | 15% | 6 |
| FastAPI endpoints + server-side RBAC + sources | 10% | 4 (`generate.py` builds the citations), 7 |
| Next.js login, badge, refusal, citations | 5% | 8 |
| Code quality, modularity, README | 5% | all; 9 |

---

## Time Budget

| Phase | Est. | Cumulative |
|---|---|---|
| 0 Environment | 1.5 h | 1.5 h |
| 1 Data inspection | 1.0 h | 2.5 h |
| 2 Ingestion | 4.0 h | 6.5 h |
| 3 Retrieval | 3.0 h | 9.5 h |
| 4 Rerank + generation | 2.5 h | 12.0 h |
| 5 Adversarial suite | 2.0 h | 14.0 h |
| 6 SQL RAG | 3.0 h | 17.0 h |
| 7 FastAPI | 3.0 h | 20.0 h |
| 8 Next.js | 4.0 h | 24.0 h |
| 9 README & submission | 2.5 h | 26.5 h |

**If you run short on time**, cut frontend polish (Phase 8 is worth 5%) before cutting the adversarial suite or the comparison harness (worth 45% between them). A plain but working UI with a rigorous README beats a beautiful UI with an unproven pipeline.

---

## Four Things That Will Bite You

1. **An empty `models.Filter()` matches everything.** Any code path that builds a filter from an unknown or missing role must *raise*, not return an empty filter. This is the difference between a 25% and a 0% on the largest rubric line.
2. **`Modifier.IDF` is mandatory for BM25 on Qdrant.** FastEmbed's `Qdrant/bm25` emits only term frequencies; IDF is corpus-dependent and computed server-side. Without the modifier you have TF-only scoring — it will still return results, which is exactly why it's dangerous.
3. **Set `max_tokens` on the tokenizer, not the chunker.** `HybridChunker(max_tokens=…)` is silently discarded. Assert `chunker.max_tokens` at startup.
4. **Inspect the SQLite value formats before writing the SQL prompt.** If `status` is `'Escalated'` and the model emits `'escalated'`, you get zero rows and a fluent, confident, wrong answer — the worst possible failure mode in a graded demo.
