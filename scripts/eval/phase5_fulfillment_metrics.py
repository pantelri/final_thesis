"""Phase 5 (Stage-3 fulfillment) — metric CSVs from the Phase-4b preds.

Reads results/preds/fulfillment_<model>_<cond>_<variant>.csv for the 2x2 factorial
(retrieval {predicted, oracle} x context {statute_only, web_enriched}) and writes:

  gt_label_distribution_fulfillment.csv  GT class counts/shares + majority baseline.
  fulfillment_metrics_per_model.csv      per (model,cond,variant): n, parse fails,
                                         accuracy (+95% bootstrap CI), macro-F1,
                                         per-class precision/recall/F1/support.
  fulfillment_confusion.csv              long gt x pred cell counts per combo.
  fulfillment_context_variants.csv       H2: web_enriched vs statute_only paired
                                         accuracy delta + 95% CI (per model,cond).
  fulfillment_retrieval_conditions.csv   predicted vs oracle paired accuracy delta
                                         + 95% CI (per model,variant).

Pure analysis, no API. Paired deltas resample the shared 141 pairs (significant iff
CI excludes 0). Run: python -m scripts.eval.phase5_fulfillment_metrics
"""
from __future__ import annotations

import csv
from collections import Counter

import numpy as np

from scripts.eval._common import (
    FULFILLMENT_CLASSES, GEN_MODELS, PREDS, RESULTS, write_csv,
)
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, bootstrap_delta_ci, prf
from scripts.eval.lib.verif_context import CONTEXT_VARIANTS
from scripts.eval.phase4b_fulfillment import RETRIEVAL_CONDS


def read_preds(model: str, cond: str, variant: str) -> list[dict]:
    path = PREDS / f"fulfillment_{model}_{cond}_{variant}.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _per_pair_correct(rows: list[dict]) -> dict[tuple[str, str], int]:
    return {(r["company_id"], r["obligation_id"]): int(r["pred_label"] == r["gt_label"])
            for r in rows if r["gt_label"] and r["pred_label"]}


def _aligned(a: dict, b: dict) -> tuple[list[int], list[int]]:
    keys = sorted(set(a) & set(b))
    return [a[k] for k in keys], [b[k] for k in keys]


def main() -> None:
    models = [m for m in GEN_MODELS
              if any((PREDS / f"fulfillment_{m}_{c}_{v}.csv").exists()
                     for c in RETRIEVAL_CONDS for v in CONTEXT_VARIANTS)]
    if not models:
        raise SystemExit("no fulfillment_<model>_<cond>_<variant>.csv preds found")

    preds, ppc = {}, {}
    for m in models:
        for c in RETRIEVAL_CONDS:
            for v in CONTEXT_VARIANTS:
                rows = read_preds(m, c, v)
                preds[(m, c, v)] = rows
                ppc[(m, c, v)] = _per_pair_correct(rows)

    # --- GT distribution + majority baseline ---
    any_rows = next(r for r in preds.values() if r)
    gt_dist = Counter(r["gt_label"] for r in any_rows if r["gt_label"])
    total = sum(gt_dist.values())
    majority = max(gt_dist.values()) / total if total else 0.0
    write_csv(RESULTS / "gt_label_distribution_fulfillment.csv",
              [{"class": c, "n": gt_dist.get(c, 0),
                "share": round(gt_dist.get(c, 0) / total, 4) if total else 0.0,
                "majority_baseline": round(majority, 4)} for c in FULFILLMENT_CLASSES],
              ["class", "n", "share", "majority_baseline"])

    metric_rows, conf_rows = [], []
    for (m, c, v), rows in preds.items():
        scored = [r for r in rows if r["gt_label"] and r["pred_label"]]
        if not scored:
            continue
        n_fail = sum(1 for r in rows if r["gt_label"] and not r["pred_label"])
        acc, lo, hi = bootstrap_acc_ci([int(r["pred_label"] == r["gt_label"]) for r in scored])
        per = {cls: prf(scored, cls) for cls in FULFILLMENT_CLASSES}
        macro = float(np.mean([per[cls][2] for cls in FULFILLMENT_CLASSES]))
        row = {"model": m, "retrieval": c, "context": v, "n_scored": len(scored),
               "n_parse_fail": n_fail, "accuracy": round(acc, 4),
               "acc_ci_lo": round(lo, 4), "acc_ci_hi": round(hi, 4), "macro_f1": round(macro, 4)}
        for cls in FULFILLMENT_CLASSES:
            p, r, f1, sup = per[cls]
            row[f"precision_{cls}"], row[f"recall_{cls}"] = round(p, 4), round(r, 4)
            row[f"f1_{cls}"], row[f"support_{cls}"] = round(f1, 4), sup
        metric_rows.append(row)
        conf = Counter((r["gt_label"], r["pred_label"]) for r in scored)
        for g in FULFILLMENT_CLASSES:
            for p in FULFILLMENT_CLASSES:
                conf_rows.append({"model": m, "retrieval": c, "context": v,
                                  "gt": g, "pred": p, "n": conf.get((g, p), 0)})

    metric_fields = (["model", "retrieval", "context", "n_scored", "n_parse_fail", "accuracy",
                      "acc_ci_lo", "acc_ci_hi", "macro_f1"]
                     + [f"{p}_{c}" for c in FULFILLMENT_CLASSES
                        for p in ("precision", "recall", "f1", "support")])
    write_csv(RESULTS / "fulfillment_metrics_per_model.csv", metric_rows, metric_fields)
    write_csv(RESULTS / "fulfillment_confusion.csv", conf_rows,
              ["model", "retrieval", "context", "gt", "pred", "n"])

    # --- H2: web_enriched vs statute_only (paired, per model x retrieval) ---
    h2_rows = []
    for m in models:
        for c in RETRIEVAL_CONDS:
            a, b = _aligned(ppc[(m, c, "web_enriched")], ppc[(m, c, "statute_only")])
            d, lo, hi = bootstrap_delta_ci(a, b)
            h2_rows.append({"model": m, "retrieval": c, "n": len(a),
                            "acc_web_enriched": round(np.mean(a), 4) if a else "",
                            "acc_statute_only": round(np.mean(b), 4) if b else "",
                            "delta_web_minus_statute": round(d, 4),
                            "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                            "significant": "yes" if (lo > 0 or hi < 0) else "no"})
    write_csv(RESULTS / "fulfillment_context_variants.csv", h2_rows,
              ["model", "retrieval", "n", "acc_web_enriched", "acc_statute_only",
               "delta_web_minus_statute", "ci_lo", "ci_hi", "significant"])

    # --- predicted vs oracle (paired, per model x context) ---
    rc_rows = []
    for m in models:
        for v in CONTEXT_VARIANTS:
            a, b = _aligned(ppc[(m, "predicted", v)], ppc[(m, "oracle", v)])
            d, lo, hi = bootstrap_delta_ci(a, b)
            rc_rows.append({"model": m, "context": v, "n": len(a),
                            "acc_predicted": round(np.mean(a), 4) if a else "",
                            "acc_oracle": round(np.mean(b), 4) if b else "",
                            "delta_predicted_minus_oracle": round(d, 4),
                            "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                            "significant": "yes" if (lo > 0 or hi < 0) else "no"})
    write_csv(RESULTS / "fulfillment_retrieval_conditions.csv", rc_rows,
              ["model", "context", "n", "acc_predicted", "acc_oracle",
               "delta_predicted_minus_oracle", "ci_lo", "ci_hi", "significant"])

    # --- console summary ---
    print(f"models: {models}")
    print(f"GT dist: " + "  ".join(f"{c}={gt_dist.get(c,0)}" for c in FULFILLMENT_CLASSES)
          + f"  (majority baseline {majority:.3f})")
    print(f"\n{'model':16} {'retr':9} {'ctx':12} {'acc':>6} {'95% CI':>15} {'macroF1':>8}")
    for row in metric_rows:
        print(f"{row['model']:16} {row['retrieval']:9} {row['context']:12} "
              f"{row['accuracy']:>6.3f} [{row['acc_ci_lo']:.3f},{row['acc_ci_hi']:.3f}] {row['macro_f1']:>8.3f}")
    print(f"\nwrote 5 CSVs to {RESULTS}")


if __name__ == "__main__":
    main()
