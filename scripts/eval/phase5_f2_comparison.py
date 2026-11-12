"""Phase 5 — F1/F2 comparison of fulfillment-pipeline output schemes.

Completeness checking is a recall-critical task: a disclosure that is actually
NOT fulfilled but flagged "fine" is a missed mandatory disclosure — the costly
error. So the headline metric is F2 (recall weighted 4x precision) on the
"needs review" class. All pipelines are scored on the SAME binary GT (140 pairs,
122 fulfilled / 18 not_fulfilled; majority baseline 0.871), winning config
qwen_3_7_max / predicted@5 / statute_only.

Pipelines (each produces a binary auditor flag: "fine" vs "needs review"):
  P1  2-option        LLM prompted with 2 options (fulfilled/not_fulfilled).
                      not_fulfilled = needs review.   [binary prompt, direct]
  P2  3-option → opt. LLM prompted with 3 options; collapse partially→fulfilled.
                      Only an explicit "not fulfilled" raises a flag. [optimistic]
  P3  3-option → cons LLM prompted with 3 options; collapse {partially,
                      not_fulfilled}→"needs review", fulfilled→"fine".
                      This is the "fine / needs review" scheme.       [conservative]

Positive ("alert") class = not_fulfilled = "needs review".
Reports per-class P/R/F1/F2, macro-F1/F2, accuracy, and a 95% bootstrap CI on the
F2 of the needs-review class. Pure analysis, no API.

Writes results/fulfillment_f2_comparison.csv and results/fulfillment_f2_comparison_md.csv.
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import RESULTS, PREDS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, prf_beta, fbeta, bootstrap_fbeta_ci

BINARY = PREDS / "fulfillmentbin_qwen_3_7_max_predicted_k5_rank.csv"
TERNARY = PREDS / "fulfillment_qwen_3_7_max_predicted_statute_only.csv"

POS = "not_fulfilled"          # = "needs review" (the alert class)
NEG = "fulfilled"              # = "fine"
CLASSES = [NEG, POS]

# 3-option → binary collapse rules
OPTIMISTIC = {"partially": "fulfilled"}        # partial counts as fine
CONSERVATIVE = {"partially": "not_fulfilled"}  # partial counts as needs-review


def _scored(predmap: dict, pairs: list, gt: dict, collapse: dict | None = None) -> list[dict]:
    rows = []
    for key in pairs:
        pred = predmap[key]
        if collapse and pred in collapse:
            pred = collapse[pred]
        rows.append({"pred_label": pred, "gt_label": gt[key],
                     "correct": int(pred == gt[key])})
    return rows


def _metrics(name: str, scored: list[dict]) -> dict:
    acc, alo, ahi = bootstrap_acc_ci([r["correct"] for r in scored])
    out = {"pipeline": name, "n": len(scored), "accuracy": round(acc, 4),
           "acc_ci_lo": round(alo, 4), "acc_ci_hi": round(ahi, 4)}
    f1s, f2s = [], []
    for c in CLASSES:
        p, r, f1, sup = prf_beta(scored, c, 1.0)
        _p, _r, f2, _s = prf_beta(scored, c, 2.0)
        f1s.append(f1)
        f2s.append(f2)
        tag = "needs_review" if c == POS else "fine"
        out |= {f"precision_{tag}": round(p, 4), f"recall_{tag}": round(r, 4),
                f"f1_{tag}": round(f1, 4), f"f2_{tag}": round(f2, 4), f"support_{tag}": sup}
    out["macro_f1"] = round(sum(f1s) / len(f1s), 4)
    out["macro_f2"] = round(sum(f2s) / len(f2s), 4)
    # bootstrap CI on the headline metric: F2 of the needs-review class
    f2pt, f2lo, f2hi = bootstrap_fbeta_ci(scored, POS, 2.0)
    out |= {"f2_needs_review_ci_lo": round(f2lo, 4), "f2_needs_review_ci_hi": round(f2hi, 4)}
    return out


def main() -> None:
    gtm = gt_master(binary=True)
    gt = {(r.company_id, r.obligation_id): r.fulfillment
          for r in gtm[gtm["fulfillment"] != ""].itertuples(index=False)}

    binp = {(r.company_id, r.obligation_id): r.pred_label
            for r in pd.read_csv(BINARY).itertuples(index=False)}
    terp = {(r.company_id, r.obligation_id): r.pred_label
            for r in pd.read_csv(TERNARY).itertuples(index=False)}

    pairs = sorted(set(gt) & set(binp) & set(terp))
    print(f"aligned pairs: {len(pairs)}  (binary GT; pos class = '{POS}' = needs review)")

    pipelines = {
        "P1_2option_binary":        _scored(binp, pairs, gt),
        "P2_3option_optimistic":    _scored(terp, pairs, gt, OPTIMISTIC),
        "P3_3option_fine_review":   _scored(terp, pairs, gt, CONSERVATIVE),
    }

    rows = [_metrics(name, sc) for name, sc in pipelines.items()]
    # reference: always-"fine" baseline (predict the majority class fulfilled)
    base_scored = [{"pred_label": NEG, "gt_label": gt[k], "correct": int(gt[k] == NEG)} for k in pairs]
    base = _metrics("majority_always_fine", base_scored)
    rows.append(base)

    df = pd.DataFrame(rows)
    out = RESULTS / "fulfillment_f2_comparison.csv"
    df.to_csv(out, index=False)

    # compact view for the writeup
    view = df[["pipeline", "accuracy", "macro_f1", "macro_f2",
               "precision_needs_review", "recall_needs_review",
               "f1_needs_review", "f2_needs_review",
               "f2_needs_review_ci_lo", "f2_needs_review_ci_hi", "support_needs_review"]]
    view.to_csv(RESULTS / "fulfillment_f2_comparison_md.csv", index=False)

    print(f"\nWrote {out}")
    print(view.to_string(index=False))


if __name__ == "__main__":
    main()
