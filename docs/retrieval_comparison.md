# Retrieval Comparison

Generated 2026-09-22 06:32 UTC by `uv run python scripts/compare_retrieval.py`.

8 probe queries, each with one hand-labelled correct chunk verified to exist in the indexed corpus. The metric is **hit@3**: is the correct chunk in the top 3 a configuration returns?

Each probe runs as a role permitted to see its answer, so this measures retrieval quality and not the access filter.

## Headline

| Configuration | hit@3 | Mean rank of correct chunk | Misses |
|---|---|---|---|
| dense only | **3/8** | 5.6 | `N95`, `SP3000`, `J44.1`, `ICD-10 code I21.4`, `what happens if I am unwell and cannot come to work` |
| bm25 only | **6/8** | 2.5 | `the insurer refused to pay, what do we do now`, `what happens if I am unwell and cannot come to work` |
| hybrid | **7/8** | 1.9 | `what happens if I am unwell and cannot come to work` |
| hybrid + rerank | **7/8** | 1.9 | `the insurer refused to pay, what do we do now` |

## Rank of the correct chunk, per probe

`-` means the correct chunk was not in the top 20 at all.

| Probe | What it probes | dense only | bm25 only | hybrid | hybrid + rerank |
|---|---|---|---|---|---|
| `N95` | Bare respirator designation, no semantic content | — | 1 | 2 | 1 |
| `SP3000` | Equipment model code as written on the asset label | 11 | 1 | 1 | 1 |
| `J44.1` | Bare ICD-10 code - near-meaningless to a dense embedder | 4 | 1 | 2 | 2 |
| `M17.0` | Second ICD-10 code, to show the first was not a fluke | 3 | 1 | 1 | 1 |
| `ICD-10 code I21.4` | Code with a little surrounding context | 5 | 2 | 2 | 2 |
| `the insurer refused to pay, what do we do now` | Paraphrase sharing almost no vocabulary with the document | 1 | 9 | 1 | 4 |
| `what happens if I am unwell and cannot come to work` | Conversational phrasing of a policy question | 14 | 4 | 5 | 3 |
| `Which gauge cannula for a paediatric patient under 5 kg?` | Clinical question carrying an exact size and unit | 1 | 1 | 1 | 1 |

## Top-3 per configuration

### `N95`

*Role:* `admin` · *Expected:* `infection_control.pdf` containing `N95`

**dense only**

1. `treatment_protocols.pdf` — C. Community-Acquired Pneumonia  
   ICD-10: J18.9…
2. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…
3. `icu_nursing_procedures.pdf` — Safety  
   GRV = gastric residual volume, checked every 4 hours. Never confirm NGT position by auscultation alone before …

**bm25 only**

1. `infection_control.pdf` — 2. PPE Selection Guide ✅  
   Routine patient contact, Gloves = Yes. Routine patient contact, Apron/Gown = No. Routine patient contact, Mask…
2. `infection_control.pdf` — 4. Transmission-Based Precautions ✅  
   Contact, Example Organisms = MRSA, VRE, C. difficile, norovirus. Contact, Key Measures = Single room preferred…
3. `infection_control.pdf` — 10. Isolation Signage ✅  
   Colour-coded door signs tell staff and visitors which precautions are in force before they enter: - Contact (y…

**hybrid**

1. `treatment_protocols.pdf` — C. Community-Acquired Pneumonia  
   ICD-10: J18.9…
2. `infection_control.pdf` — 2. PPE Selection Guide ✅  
   Routine patient contact, Gloves = Yes. Routine patient contact, Apron/Gown = No. Routine patient contact, Mask…
3. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…

**hybrid + rerank**

1. `infection_control.pdf` — 10. Isolation Signage ✅  
   Colour-coded door signs tell staff and visitors which precautions are in force before they enter: - Contact (y…
2. `infection_control.pdf` — 2. PPE Selection Guide ✅  
   Routine patient contact, Gloves = Yes. Routine patient contact, Apron/Gown = No. Routine patient contact, Mask…
3. `infection_control.pdf` — 4. Transmission-Based Precautions ✅  
   Contact, Example Organisms = MRSA, VRE, C. difficile, norovirus. Contact, Key Measures = Single room preferred…

### `SP3000`

*Role:* `admin` · *Expected:* `equipment_manual.pdf` containing `SP3000`

**dense only**

1. `equipment_manual.pdf` — Alarm parameter defaults and adjustable ranges  
   SpO₂, Default Low = 90%. SpO₂, Default High = 100%. SpO₂, Adjustable Range = 80-100%. Heart Rate, Default Low …
2. `icu_nursing_procedures.pdf` — Hourly monitoring  
   - SpO₂, end-tidal CO₂ (EtCO₂) - Peak and plateau airway pressures - Delivered tidal volume - Ventilator alarm …
3. `equipment_manual.pdf` — A. Patient Monitoring System - MediAssist BM-500  
   Multi-parameter monitor for ECG, SpO₂, NIBP, respiratory rate and temperature. 12-inch colour display; interna…

**bm25 only**

1. `equipment_manual.pdf` — C. Autoclave Steriliser - SterilPro 3000 ✅  
   134-litre chamber steam steriliser supporting gravity and pre-vacuum cycles, validated for wrapped instruments…

**hybrid**

1. `equipment_manual.pdf` — C. Autoclave Steriliser - SterilPro 3000 ✅  
   134-litre chamber steam steriliser supporting gravity and pre-vacuum cycles, validated for wrapped instruments…
2. `equipment_manual.pdf` — Alarm parameter defaults and adjustable ranges  
   SpO₂, Default Low = 90%. SpO₂, Default High = 100%. SpO₂, Adjustable Range = 80-100%. Heart Rate, Default Low …
3. `icu_nursing_procedures.pdf` — Hourly monitoring  
   - SpO₂, end-tidal CO₂ (EtCO₂) - Peak and plateau airway pressures - Delivered tidal volume - Ventilator alarm …

**hybrid + rerank**

1. `equipment_manual.pdf` — C. Autoclave Steriliser - SterilPro 3000 ✅  
   134-litre chamber steam steriliser supporting gravity and pre-vacuum cycles, validated for wrapped instruments…
2. `equipment_manual.pdf` — A. Patient Monitoring System - MediAssist BM-500  
   Multi-parameter monitor for ECG, SpO₂, NIBP, respiratory rate and temperature. 12-inch colour display; interna…
3. `equipment_manual.pdf` — F. Preventive Maintenance Calendar (summary)  
   BM-500 Monitor, Daily = Clean, battery. BM-500 Monitor, Weekly = -. BM-500 Monitor, Monthly = SpO₂ check; NIBP…

### `J44.1`

*Role:* `admin` · *Expected:* `billing_codes.pdf` containing `J44.1`

**dense only**

1. `treatment_protocols.pdf` — G. Acute Exacerbation of COPD  
   ICD-10: J44.1…
2. `treatment_protocols.pdf` — C. Community-Acquired Pneumonia  
   ICD-10: J18.9…
3. `equipment_manual.pdf` — Fault codes  
   F-01, Meaning = Air in line. F-01, Action = Purge line; check connections. F-03, Meaning = Occlusion. F-03, Ac…

**bm25 only**

1. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
2. `treatment_protocols.pdf` — G. Acute Exacerbation of COPD  
   ICD-10: J44.1…
3. `treatment_protocols.pdf` — Management  
   Intervention, 1 = Detail. Controlled oxygen, 1 = Target SpO₂ 88-92%; venturi mask; avoid over-oxygenation. Bro…

**hybrid**

1. `treatment_protocols.pdf` — G. Acute Exacerbation of COPD  
   ICD-10: J44.1…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `treatment_protocols.pdf` — C. Community-Acquired Pneumonia  
   ICD-10: J18.9…

**hybrid + rerank**

1. `treatment_protocols.pdf` — G. Acute Exacerbation of COPD  
   ICD-10: J44.1…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist  
   LOS = 1-2 days. S52.5, Package (₹) = ₹38,000. S52.5, Pre-auth = Yes. M17.0, Description = Primary osteoarthrit…

### `M17.0`

*Role:* `admin` · *Expected:* `billing_codes.pdf` containing `M17.0`

**dense only**

1. `icu_nursing_procedures.pdf` — Equipment checklist  
   - Sterile gloves and sterile dressing pack - Chlorhexidine 2% in 70% alcohol solution - Sterile drape - Transp…
2. `equipment_manual.pdf` — F. Preventive Maintenance Calendar (summary)  
   BM-500 Monitor, Daily = Clean, battery. BM-500 Monitor, Weekly = -. BM-500 Monitor, Monthly = SpO₂ check; NIBP…
3. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   LOS = 1-2 days. S52.5, Package (₹) = ₹38,000. S52.5, Pre-auth = Yes. M17.0, Description = Primary osteoarthrit…

**bm25 only**

1. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   LOS = 1-2 days. S52.5, Package (₹) = ₹38,000. S52.5, Pre-auth = Yes. M17.0, Description = Primary osteoarthrit…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `drug_formulary.pdf` — 11. IV Fluids Quick Reference  
   0.9% Sodium Chloride, Tonicity = Isotonic. 0.9% Sodium Chloride, Typical Use = Resuscitation, maintenance. Rin…

**hybrid**

1. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   LOS = 1-2 days. S52.5, Package (₹) = ₹38,000. S52.5, Pre-auth = Yes. M17.0, Description = Primary osteoarthrit…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `icu_nursing_procedures.pdf` — Equipment checklist  
   - Sterile gloves and sterile dressing pack - Chlorhexidine 2% in 70% alcohol solution - Sterile drape - Transp…

**hybrid + rerank**

1. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   LOS = 1-2 days. S52.5, Package (₹) = ₹38,000. S52.5, Pre-auth = Yes. M17.0, Description = Primary osteoarthrit…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `staff_handbook.pdf` — 12. Emergency Codes  
   MediAssist uses a standard colour-code system across all campuses. Every employee must memorise these codes ir…

### `ICD-10 code I21.4`

*Role:* `admin` · *Expected:* `billing_codes.pdf` containing `I21.4`

**dense only**

1. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…
2. `treatment_protocols.pdf` — E. Paediatric Fever Management  
   ICD-10: R50.9…
3. `treatment_protocols.pdf` — C. Community-Acquired Pneumonia  
   ICD-10: J18.9…

**bm25 only**

1. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 1. Cashless Claim Process > 1.5 Worked example  
   A patient is admitted at 9:00 pm with chest pain; provisional diagnosis **NSTEMI (I21.4)** , package rate **₹1…

**hybrid**

1. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `treatment_protocols.pdf` — E. Paediatric Fever Management  
   ICD-10: R50.9…

**hybrid + rerank**

1. `treatment_protocols.pdf` — D. Acute Myocardial Infarction - NSTEMI  
   ICD-10: I21.4…
2. `billing_codes.pdf` — 1. Top 30 Diagnosis Codes Used at MediAssist ✅  
   I21.0, Description = STEMI - anterior wall. I21.0, Typical LOS = 5-7 days. I21.0, Package (₹) = ₹1,85,000. I21…
3. `treatment_protocols.pdf` — B. Hypertension - Stage 2  
   ICD-10: I10…

### `the insurer refused to pay, what do we do now`

*Role:* `admin` · *Expected:* `claim_submission_guide.md` section `4. Claim Rejection Response`

**dense only**

1. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.3 Deadlines ✅  
   - Reconsideration / appeal must be filed within the insurer's window — **usually 90 days** from rejection. - I…
2. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.2 Counter-response template ✅  
   **Subject:** Reconsideration request — Claim [CLM-2024-XXXX] / Pre-auth [number] Dear [Insurer/TPA], We reques…
3. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 2. Reimbursement Claim Process > 2.2 Step-by-step  
   1. Counsel the patient at discharge that the claim is reimbursement, not cashless. 2. Issue the complete origi…

**bm25 only**

1. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 1. Cashless Claim Process  
   Cashless is the default pathway for **planned and emergency admissions** where the patient holds a policy with…
2. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 2. Reimbursement Claim Process  
   Used when the patient **pays the hospital directly** and claims from the insurer afterwards — typically when t…
3. `billing_codes.pdf` — Note  
   Package rates below are indicative MediAssist negotiated rates. Final settlement depends on the patient's poli…

**hybrid**

1. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 4. Claim Rejection Response > 4.3 Deadlines ✅  
   - Reconsideration / appeal must be filed within the insurer's window — **usually 90 days** from rejection. - I…
2. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 1. Cashless Claim Process  
   Cashless is the default pathway for **planned and emergency admissions** where the patient holds a policy with…
3. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 2. Reimbursement Claim Process  
   Used when the patient **pays the hospital directly** and claims from the insurer afterwards — typically when t…

**hybrid + rerank**

1. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 2. Reimbursement Claim Process  
   Used when the patient **pays the hospital directly** and claims from the insurer afterwards — typically when t…
2. `claim_submission_guide.md` — Claim Submission & Escalation Guide > Purpose & Scope  
   This guide is the standard operating reference for billing executives handling insurance claims at any MediAss…
3. `claim_submission_guide.md` — Claim Submission & Escalation Guide > 1. Cashless Claim Process  
   Cashless is the default pathway for **planned and emergency admissions** where the patient holds a policy with…

### `what happens if I am unwell and cannot come to work`

*Role:* `admin` · *Expected:* `leave_policy.pdf` section `2. Leave Types and Entitlements`

**dense only**

1. `leave_policy.pdf` — 8. Leave Without Pay (LOP) & Special Cases  
   - Leave Without Pay (LOP) is granted only when paid leave is exhausted and requires HOD plus HR approval; it d…
2. `leave_policy.pdf` — Important  
   Absence from duty without information for 10 or more consecutive days is treated as voluntary abandonment of s…
3. `icu_nursing_procedures.pdf` — Safety  
   Stop suctioning immediately for SpO₂ < 90%, bradycardia, or a new arrhythmia, and re-oxygenate the patient.…

**bm25 only**

1. `equipment_manual.pdf` — High-alert drug protocols (drug library)  
   The following carry hard limits (cannot be overridden) and soft limits (require confirmation): Dopamine, Dobut…
2. `claim_submission_guide.md` — Claim Submission & Escalation Guide > Purpose & Scope  
   This guide is the standard operating reference for billing executives handling insurance claims at any MediAss…
3. `staff_handbook.pdf` — 5. Working Hours & Shifts  
   Working patterns differ between administrative and clinical staff. - Standard office hours (administrative, bi…

**hybrid**

1. `equipment_manual.pdf` — High-alert drug protocols (drug library)  
   The following carry hard limits (cannot be overridden) and soft limits (require confirmation): Dopamine, Dobut…
2. `leave_policy.pdf` — 8. Leave Without Pay (LOP) & Special Cases  
   - Leave Without Pay (LOP) is granted only when paid leave is exhausted and requires HOD plus HR approval; it d…
3. `leave_policy.pdf` — Important  
   Absence from duty without information for 10 or more consecutive days is treated as voluntary abandonment of s…

**hybrid + rerank**

1. `leave_policy.pdf` — Important  
   Absence from duty without information for 10 or more consecutive days is treated as voluntary abandonment of s…
2. `general_faqs.pdf` — Q22. What is the fire evacuation procedure?  
   On hearing the fire alarm, stop work, help any patients nearby, and proceed calmly to the nearest fire exit an…
3. `leave_policy.pdf` — 2. Leave Types and Entitlements ✅  
   Leave entitlements differ between clinical staff (doctors and nurses) and non-clinical staff, reflecting roste…

### `Which gauge cannula for a paediatric patient under 5 kg?`

*Role:* `admin` · *Expected:* `icu_nursing_procedures.pdf` containing `24G`

**dense only**

1. `icu_nursing_procedures.pdf` — Cannula sizing by indication ✅  
   Blood transfusion, Recommended Gauge = ≥ 18G. Rapid fluid resuscitation, Recommended Gauge = ≥ 16G. Routine me…
2. `icu_nursing_procedures.pdf` — Cannula change  
   Replace every 72-96 hours , or immediately if there are signs of phlebitis (Visual Infusion Phlebitis [VIP] sc…
3. `icu_nursing_procedures.pdf` — Ventilator bundle (VAP prevention)  
   - Head of bed (HOB) elevation 30-45° - Oral care with chlorhexidine every 4 hours - Subglottic suctioning wher…

**bm25 only**

1. `icu_nursing_procedures.pdf` — Cannula sizing by indication ✅  
   Blood transfusion, Recommended Gauge = ≥ 18G. Rapid fluid resuscitation, Recommended Gauge = ≥ 16G. Routine me…
2. `treatment_protocols.pdf` — Weight-based dosing  
   < 5 kg, Paracetamol (oral) = 60 mg Q6H. < 5 kg, Ibuprofen (oral) = Not recommended. < 5 kg, IV Paracetamol = 7…
3. `equipment_manual.pdf` — Technique chart  
   Chest AP (adult), kVp = 90. Chest AP (adult), mAs = 5. Chest AP (adult), Grid = No. Chest AP (adult), Notes = …

**hybrid**

1. `icu_nursing_procedures.pdf` — Cannula sizing by indication ✅  
   Blood transfusion, Recommended Gauge = ≥ 18G. Rapid fluid resuscitation, Recommended Gauge = ≥ 16G. Routine me…
2. `icu_nursing_procedures.pdf` — Cannula change  
   Replace every 72-96 hours , or immediately if there are signs of phlebitis (Visual Infusion Phlebitis [VIP] sc…
3. `equipment_manual.pdf` — Technique chart  
   Chest AP (adult), kVp = 90. Chest AP (adult), mAs = 5. Chest AP (adult), Grid = No. Chest AP (adult), Notes = …

**hybrid + rerank**

1. `icu_nursing_procedures.pdf` — Cannula sizing by indication ✅  
   Blood transfusion, Recommended Gauge = ≥ 18G. Rapid fluid resuscitation, Recommended Gauge = ≥ 16G. Routine me…
2. `icu_nursing_procedures.pdf` — Sizing  
   Adult: 14-16 Fr . Paediatric: select by age-appropriate formula.…
3. `treatment_protocols.pdf` — E. Paediatric Fever Management  
   ICD-10: R50.9…
