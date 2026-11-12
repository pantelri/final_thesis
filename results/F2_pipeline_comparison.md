# Fulfillment Output Scheme — F1 / F2 Comparison

**Date:** 2026-06-30
**Script:** `scripts/eval/phase5_f2_comparison.py`
**Data:** `results/fulfillment_f2_comparison.csv` (full), `results/fulfillment_f2_comparison_md.csv` (compact)
**Config:** winning fulfillment config `qwen_3_7_max / predicted@5 (rank) / statute_only`
**Ground truth:** binary GT, 140 scored pairs — **122 fulfilled / 18 not_fulfilled**

---

## 1. Why F2, and what is the positive class

Completeness checking is a **recall-critical** task. The expensive error is a
disclosure that is *actually missing* but the tool reports as "fine" — a missed
mandatory disclosure slips past the auditor. A false alarm (flagging a fulfilled
disclosure for review) only costs a few seconds of the auditor's time.

We therefore report **F2** (the F-measure with β = 2, which weights **recall 4×
as heavily as precision**) in addition to F1, and we compute it on the **alert
class = "needs review" (= `not_fulfilled`)**. This matches the papers that
benchmark completeness-checking pipelines on F2 rather than accuracy.

> **Accuracy is a trap here.** The GT is imbalanced (122 : 18), so a classifier
> that *always* says "fine" scores **0.871 accuracy** while finding **zero**
> incomplete disclosures (F2 = 0). Accuracy rewards doing nothing; F2 on the
> needs-review class does not.

---

## 2. The three pipelines compared

All three take the **same winning retrieval + model**; they differ only in how
the fulfillment verdict is produced and mapped to the binary auditor flag
("fine" vs "needs review").

| ID | Pipeline | Prompt | Mapping to "needs review" |
|----|----------|--------|----------------------------|
| **P1** | **2-option** | LLM chooses `fulfilled` / `not_fulfilled` | `not_fulfilled` → needs review |
| **P2** | **3-option, optimistic** | LLM chooses `fulfilled` / `partially` / `not_fulfilled` | only `not_fulfilled` → needs review; `partially` counts as fine |
| **P3** | **3-option, "fine / needs review"** | same 3-option prompt | **`partially` *and* `not_fulfilled` → needs review**; only `fulfilled` → fine |

P3 is the scheme you described: the model still reasons over three options, but
the output collapses into two — **"fine"** (fulfilled) vs **"needs review"**
(not fulfilled *or* merely partial). `majority_always_fine` is the do-nothing
reference.

---

## 3. Results

Headline metric in **bold** (F2 on the needs-review class). Support of the
needs-review class = 18 in every row.

| Pipeline | Accuracy | macro-F1 | macro-F2 | Precision (review) | Recall (review) | F1 (review) | **F2 (review)** | F2 95% CI |
|----------|:--------:|:--------:|:--------:|:------------------:|:---------------:|:-----------:|:---------------:|:---------:|
| **P3 — 3-option, fine/needs-review** | 0.721 | 0.609 | **0.652** | 0.277 | **0.722** | 0.400 | **0.546** | [0.361, 0.697] |
| **P1 — 2-option (binary prompt)** | 0.757 | 0.610 | 0.637 | 0.278 | 0.556 | 0.370 | **0.463** | [0.269, 0.636] |
| **P2 — 3-option, optimistic** | 0.850 | 0.570 | 0.561 | 0.333 | 0.167 | 0.222 | **0.185** | [0.000, 0.390] |
| majority "always fine" | 0.871 | 0.466 | 0.486 | 0.000 | 0.000 | 0.000 | 0.000 | — |

---

## 4. Interpretation

- **P3 (3-option → fine/needs-review) is the best pipeline for the audit task.**
  It has the **highest recall of incomplete disclosures (0.722)**, the highest
  **F2 (0.546)** and the highest **macro-F2 (0.652)**. Treating "partially" as a
  reason to review is exactly the auditor-conservative behaviour you want: it
  surfaces the borderline cases instead of silently passing them.

- **P1 (2-option) is the middle ground.** Forcing a binary decision in the
  prompt collapses the model's uncertainty; recall drops to 0.556 and F2 to
  0.463. It is simpler and slightly more accurate than P3, but it catches fewer
  gaps. Its F2 CI overlaps P3's, so the F2 advantage of P3 over P1 is directional
  rather than statistically separated at n = 18 positives.

- **P2 (3-option, optimistic) looks good on accuracy (0.850) and is the worst
  pipeline for the task.** Hiding "partially" inside "fine" suppresses almost all
  alerts (recall 0.167, F2 0.185). This is the accuracy trap in action — high
  accuracy bought by not flagging.

- **None of the pipelines beats the do-nothing accuracy (0.871)**, which is *only*
  meaningful evidence that accuracy is the wrong yardstick. On F2 — the metric
  that actually rewards finding incomplete disclosures — every working pipeline
  beats the 0.000 of the do-nothing baseline, and P3 beats it by the most.

---

## 5. Recommendation

For a completeness-check tool whose job is to **not miss** mandatory disclosures,
**continue with the 3-option pipeline read out as "fine / needs review" (P3).**
It maximises recall and F2 on the incomplete class while keeping the model's
"partially" nuance as a review trigger. Choose the plain 2-option pipeline (P1)
only if you specifically want fewer review flags at the cost of missing ~17% more
incomplete disclosures.

**Caveats:** the not_fulfilled / needs-review class has only 18 instances, so the
F2 confidence intervals are wide and P3-vs-P1 is not significant; the ranking
P3 > P1 > P2 is, however, consistent across recall, F1 and F2.

---

## 6. Reproduce

```powershell
$env:PYTHONPATH = "C:\Users\Sellit\Documents\Masterarbeit\source_code"
$env:PYTHONIOENCODING = "utf-8"
python -m scripts.eval.phase5_f2_comparison
```

No API calls — pure re-scoring of the cached qwen predictions
(`fulfillmentbin_qwen_3_7_max_predicted_k5_rank.csv` for P1;
`fulfillment_qwen_3_7_max_predicted_statute_only.csv` for P2/P3).
