# Cross-Encoder Reranking Log

Generated 2026-09-22 06:37 UTC by `uv run python scripts/rerank_demo.py`.

Hybrid retrieval scores the query and each chunk **independently** - the two
embeddings are computed without knowledge of each other. A cross-encoder reads
the pair **together** in one forward pass. That is far more accurate, and far
too slow to run over a whole corpus, which is why it runs on 20 candidates
rather than 256 chunks.

Only the top 3 after reranking are passed to the LLM, and
only if they clear the relevance floor. Rows in **bold** are the ones that
actually reached the prompt.

Scores are in (0, 1) because the model is loaded with an explicit sigmoid activation. The relevance floor is `0.05` - below it, the role-scoped refusal is returned instead of an answer.

## `What size cannula should I use for a baby under 5 kg?`

*Role:* `nurse`

| hybrid rank | rerank score | new rank | move | source | section |
|---|---|---|---|---|---|
| 1 | **0.4178** | **1** | - | `icu_nursing_procedures.pdf` | Cannula sizing by indication |
| 2 | 0.0001 | 2 | - | `icu_nursing_procedures.pdf` | Cannula change |
| 4 | 0.0000 | 3 | +1 | `icu_nursing_procedures.pdf` | Initial settings |
| 3 | 0.0000 | 4 | -1 | `icu_nursing_procedures.pdf` | Sizing |
| 9 | 0.0000 | 5 | +4 | `icu_nursing_procedures.pdf` | Procedure |
| 6 | 0.0000 | 6 | - | `icu_nursing_procedures.pdf` | Procedure |
| 17 | 0.0000 | 7 | +10 | `staff_handbook.pdf` | 12. Emergency Codes |
| 8 | 0.0000 | 8 | - | `staff_handbook.pdf` | 1. About MediAssist Health Network |
| 12 | 0.0000 | 9 | +3 | `icu_nursing_procedures.pdf` | Insertion procedure |
| 14 | 0.0000 | 10 | +4 | `icu_nursing_procedures.pdf` | Feeding & gastric residual monitoring |
| 11 | 0.0000 | 11 | - | `icu_nursing_procedures.pdf` | Alarm response |
| 7 | 0.0000 | 12 | -5 | `code_of_conduct.pdf` | 5. Gifts & Gratuity |
| 18 | 0.0000 | 13 | +5 | `infection_control.pdf` | 4. Transmission-Based Precautions |
| 10 | 0.0000 | 14 | -4 | `icu_nursing_procedures.pdf` | Preventive bundle |
| 16 | 0.0000 | 15 | +1 | `staff_handbook.pdf` | 9. IT & Systems Access |
| 13 | 0.0000 | 16 | -3 | `icu_nursing_procedures.pdf` | Ventilator bundle (VAP prevention) |
| 19 | 0.0000 | 17 | +2 | `icu_nursing_procedures.pdf` | Equipment checklist |
| 5 | 0.0000 | 18 | -13 | `icu_nursing_procedures.pdf` | Safety |
| 20 | 0.0000 | 19 | +1 | `infection_control.pdf` | Prevention |
| 15 | 0.0000 | 20 | -5 | `general_faqs.pdf` | Q10. Is personal use of hospital Wi-Fi permitted? |

Largest promotion: **10 places**.

## `N95`

*Role:* `nurse`

| hybrid rank | rerank score | new rank | move | source | section |
|---|---|---|---|---|---|
| 6 | **0.9814** | **1** | +5 | `infection_control.pdf` | 10. Isolation Signage |
| 1 | **0.9768** | **2** | -1 | `infection_control.pdf` | 2. PPE Selection Guide |
| 4 | **0.8570** | **3** | +1 | `infection_control.pdf` | 4. Transmission-Based Precautions |
| 16 | 0.0000 | 4 | +12 | `staff_handbook.pdf` | Text-based org chart |
| 3 | 0.0000 | 5 | -2 | `staff_handbook.pdf` | 12. Emergency Codes |
| 19 | 0.0000 | 6 | +13 | `staff_handbook.pdf` | 13. Key Contacts |
| 8 | 0.0000 | 7 | +1 | `general_faqs.pdf` | Q11. Who do I contact for a clinical software issue during a shift? |
| 18 | 0.0000 | 8 | +10 | `icu_nursing_procedures.pdf` | Alarm response |
| 15 | 0.0000 | 9 | +6 | `leave_policy.pdf` | 9. Public Holiday List (illustrative) |
| 17 | 0.0000 | 10 | +7 | `icu_nursing_procedures.pdf` | Procedure |
| 12 | 0.0000 | 11 | +1 | `icu_nursing_procedures.pdf` | Staging quick reference |
| 5 | 0.0000 | 12 | -7 | `icu_nursing_procedures.pdf` | Equipment checklist |
| 11 | 0.0000 | 13 | -2 | `leave_policy.pdf` | Important |
| 14 | 0.0000 | 14 | - | `icu_nursing_procedures.pdf` | Cannula change |
| 2 | 0.0000 | 15 | -13 | `icu_nursing_procedures.pdf` | Safety |
| 7 | 0.0000 | 16 | -9 | `icu_nursing_procedures.pdf` | Ventilator bundle (VAP prevention) |
| 13 | 0.0000 | 17 | -4 | `icu_nursing_procedures.pdf` | Insertion procedure |
| 9 | 0.0000 | 18 | -9 | `icu_nursing_procedures.pdf` | Safety |
| 10 | 0.0000 | 19 | -9 | `icu_nursing_procedures.pdf` | Preventive bundle |
| 20 | 0.0000 | 20 | - | `leave_policy.pdf` | Approval rule |

Largest promotion: **13 places**.

## `How do I respond when an insurer rejects a claim?`

*Role:* `billing_executive`

| hybrid rank | rerank score | new rank | move | source | section |
|---|---|---|---|---|---|
| 1 | **0.9985** | **1** | - | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.3 Deadlines |
| 3 | **0.9971** | **2** | +1 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.2 Counter-response template |
| 5 | **0.9748** | **3** | +2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 4. Claim Rejection Response |
| 10 | 0.9508 | 4 | +6 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.1 Common rejection codes |
| 4 | 0.9067 | 5 | -1 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 5. Escalation Matrix |
| 8 | 0.8973 | 6 | +2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > Purpose & Scope |
| 9 | 0.8516 | 7 | +2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > Quick Reference Card |
| 6 | 0.6568 | 8 | -2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 2. Reimbursement Claim Process > 2.2 Step-by-step |
| 7 | 0.4730 | 9 | -2 | `billing_codes.pdf` | 4. Exclusions Reference |
| 2 | 0.2914 | 10 | -8 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 1. Cashless Claim Process > 1.3 Step-by-step |
| 15 | 0.1589 | 11 | +4 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 2. Reimbursement Claim Process |
| 13 | 0.0979 | 12 | +1 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 7. Key Performance Indicators (KPIs) |
| 12 | 0.0951 | 13 | -1 | `billing_codes.pdf` | Introduction |
| 16 | 0.0716 | 14 | +2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 3. Pre-Authorisation Enhancement > 3.3 Process |
| 14 | 0.0122 | 15 | -1 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 1. Cashless Claim Process > 1.2 Documents required for pre-authorisation |
| 19 | 0.0085 | 16 | +3 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > 1. Cashless Claim Process |
| 18 | 0.0053 | 17 | +1 | `claim_submission_guide.md` | Claim Submission & Escalation Guide > Purpose & Scope > How claims flow at MediAssist |
| 11 | 0.0040 | 18 | -7 | `billing_codes.pdf` | 3. Empanelled Insurer Panel |
| 17 | 0.0003 | 19 | -2 | `claim_submission_guide.md` | Claim Submission & Escalation Guide |
| 20 | 0.0000 | 20 | - | `code_of_conduct.pdf` | 10. Anti-Bribery & Anti-Corruption |

Largest promotion: **6 places**.

## `Which fault codes mean the X-ray unit must be removed from service?`

*Role:* `technician`

| hybrid rank | rerank score | new rank | move | source | section |
|---|---|---|---|---|---|
| 2 | **0.9981** | **1** | +1 | `equipment_manual.pdf` | Remove from service |
| 4 | **0.9856** | **2** | +2 | `equipment_manual.pdf` | Remove from service |
| 1 | **0.9681** | **3** | -2 | `equipment_manual.pdf` | E. Maintenance & Fault-Code Summary |
| 3 | 0.8764 | 4 | -1 | `equipment_manual.pdf` | Fault codes |
| 5 | 0.6554 | 5 | - | `equipment_manual.pdf` | Fault codes |
| 6 | 0.5909 | 6 | - | `equipment_manual.pdf` | Fault codes |
| 7 | 0.0292 | 7 | - | `equipment_manual.pdf` | Fault codes |
| 9 | 0.0018 | 8 | +1 | `equipment_manual.pdf` | D. Portable X-Ray Unit - RadiPro MX-150 |
| 11 | 0.0006 | 9 | +2 | `equipment_manual.pdf` | Conventions |
| 13 | 0.0004 | 10 | +3 | `equipment_manual.pdf` | Record-keeping |
| 16 | 0.0001 | 11 | +5 | `equipment_manual.pdf` | Radiation safety |
| 10 | 0.0001 | 12 | -2 | `equipment_manual.pdf` | Mandatory |
| 12 | 0.0000 | 13 | -1 | `staff_handbook.pdf` | 12. Emergency Codes |
| 8 | 0.0000 | 14 | -6 | `equipment_manual.pdf` | I. Common Operator Errors & Troubleshooting |
| 20 | 0.0000 | 15 | +5 | `equipment_manual.pdf` | Battery & preventive maintenance |
| 14 | 0.0000 | 16 | -2 | `leave_policy.pdf` | 8. Leave Without Pay (LOP) & Special Cases |
| 19 | 0.0000 | 17 | +2 | `general_faqs.pdf` | Q7. How do I reset my password for MediAssist systems? |
| 15 | 0.0000 | 18 | -3 | `code_of_conduct.pdf` | Gross misconduct |
| 17 | 0.0000 | 19 | -2 | `general_faqs.pdf` | Q11. Who do I contact for a clinical software issue during a shift? |
| 18 | 0.0000 | 20 | -2 | `staff_handbook.pdf` | 6. Staff ID & Access Cards |

Largest promotion: **5 places**.

## `How much earned leave do clinical staff get?`

*Role:* `doctor`

| hybrid rank | rerank score | new rank | move | source | section |
|---|---|---|---|---|---|
| 1 | **0.9956** | **1** | - | `leave_policy.pdf` | 2. Leave Types and Entitlements |
| 9 | **0.6358** | **2** | +7 | `leave_policy.pdf` | 6. Public Holidays |
| 8 | **0.5063** | **3** | +5 | `staff_handbook.pdf` | 10. Probation & Confirmation |
| 4 | 0.4242 | 4 | - | `general_faqs.pdf` | Q19. What is the notice period for resignation? |
| 3 | 0.0669 | 5 | -2 | `staff_handbook.pdf` | Weekly off policy |
| 2 | 0.0483 | 6 | -4 | `leave_policy.pdf` | 7. Leave Encashment |
| 10 | 0.0362 | 7 | +3 | `staff_handbook.pdf` | 11. Training & Professional Development |
| 11 | 0.0288 | 8 | +3 | `leave_policy.pdf` | 5. On-Call & Duty Roster |
| 6 | 0.0068 | 9 | -3 | `staff_handbook.pdf` | 5. Working Hours & Shifts |
| 20 | 0.0056 | 10 | +10 | `general_faqs.pdf` | Q5. What health insurance is provided to staff? |
| 5 | 0.0040 | 11 | -6 | `leave_policy.pdf` | 8. Leave Without Pay (LOP) & Special Cases |
| 7 | 0.0017 | 12 | -5 | `leave_policy.pdf` | 3. Leave Application Process |
| 15 | 0.0005 | 13 | +2 | `staff_handbook.pdf` | Patient First |
| 14 | 0.0005 | 14 | - | `code_of_conduct.pdf` | 6. Substance Abuse |
| 12 | 0.0003 | 15 | -3 | `staff_handbook.pdf` | 6. Staff ID & Access Cards |
| 19 | 0.0002 | 16 | +3 | `general_faqs.pdf` | Q17. Who approves leave for doctors in the ICU department? |
| 17 | 0.0000 | 17 | - | `staff_handbook.pdf` | Text-based org chart |
| 18 | 0.0000 | 18 | - | `leave_policy.pdf` | Leave & Attendance Policy |
| 16 | 0.0000 | 19 | -3 | `staff_handbook.pdf` | 2. Organisational Structure |
| 13 | 0.0000 | 20 | -7 | `general_faqs.pdf` | Q18. How do I get an experience letter or employment certificate? |

Largest promotion: **10 places**.
