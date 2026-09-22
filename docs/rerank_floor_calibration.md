# Relevance Floor Calibration

Generated 2026-09-22 08:10 UTC by `uv run python scripts/calibrate_floor.py`.

Current `RERANK_MIN_SCORE` = **0.002**

Cross-encoder scores are **not calibrated across queries**. The model is
sharply bimodal — a confident match scores ~0.98, an unrelated chunk ~0.000x —
but a *weakly phrased* correct match can land an order of magnitude lower than
a well-phrased one. So the floor is an empirical choice and has to be
re-derived whenever the corpus, the embedder or the reranker changes.

Getting it wrong is asymmetric, and the two failures look nothing alike:

- **Too high** → correct answers are refused. This is the dangerous direction,
  because a false refusal is visually identical to RBAC working correctly.
- **Too low** → the LLM is handed irrelevant context and may improvise.

| Expected | Role | Top rerank score | Verdict | Question |
|---|---|---:|---|---|
| REFUSE | `billing_executive` | 0.000022 | ✅ | What is the ventilator bundle for VAP prevention? |
| REFUSE | `nurse` | 0.000029 | ✅ | What is the package rate for a pacemaker implant? |
| REFUSE | `technician` | 0.000029 | ✅ | How do I insert a nasogastric tube? |
| REFUSE | `technician` | 0.000053 | ✅ | What is the standard dose of amlodipine? |
| REFUSE | `doctor` | 0.000096 | ✅ | Which fault codes require removing the X-ray unit? |
| REFUSE | `technician` | 0.000097 | ✅ | What is the standard dosage of amiodarone for adult cardiac arrest? |
| REFUSE | `nurse` | 0.000141 | ✅ | Show me all insurance billing codes |
| REFUSE | `nurse` | 0.000323 | ✅ | What are the normal arterial blood gas ranges? |
| ANSWER | `technician` | 0.005906 | ✅ | What is the preventive maintenance schedule for the autoclave? |
| ANSWER | `nurse` | 0.014081 | ✅ | What is the escalation procedure if a cannula site looks infected? |
| ANSWER | `nurse` | 0.901826 | ✅ | How many cannulation attempts before escalating? |
| ANSWER | `nurse` | 0.975905 | ✅ | What colour bin is used for biomedical waste? |
| ANSWER | `technician` | 0.996356 | ✅ | What does fault code E-01 mean on the autoclave? |
| ANSWER | `nurse` | 0.998330 | ✅ | What defines an outbreak? |
| ANSWER | `technician` | 0.999376 | ✅ | What is the default occlusion pressure alarm? |
| ANSWER | `technician` | 0.999385 | ✅ | What is the carry-forward cap on earned leave? |
| ANSWER | `billing_executive` | 0.999475 | ✅ | What is the appeal deadline for a rejected claim? |
| ANSWER | `doctor` | 0.999590 | ✅ | What is the normal haemoglobin range for a male? |

## Separation

| Metric | Value |
|---|---|
| Highest score among should-refuse | `0.000323` |
| Lowest score among should-answer | `0.005906` |
| Separable | **True** |
| Suggested floor (geometric midpoint) | `0.001382` |
| Configured floor | `0.002` |
| Margin below the lowest correct answer | 3.0× |
| Margin above the highest correct refusal | 6.2× |
| Misclassified at the configured floor | **0** |
