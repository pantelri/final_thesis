"""Phase 5 (Stage-1 relevance) — the canonical relevance metric CSVs.

Reads results/preds/relevance_<model>.csv (company_id, obligation_id, pred_label,
gt_label, correct, reason) for every GEN_MODELS key with a preds file, plus the
Stage-1 ground truth (`_load_gt.gt_master()`) and the obligation catalogue
(`Requirements/offenlegungspflichten_gefiltert.csv`). Writes into results/:

  gt_label_distribution_relevance.csv  GT class counts/shares (stage-1).
  relevance_metrics_per_model.csv      accuracy and macro-F1 (both with 95%
                                       bootstrap CI), per-class P/R/F1, n_scored.
  relevance_confusion.csv              long-format gt x pred cell counts/model.
  relevance_gt_per_requirement.csv     per-obligation GT composition + cluster keys.
  relevance_per_requirement.csv        per (model, obligation): accuracy, macro-F1
                                       (undefined for single-GT-class obligations),
                                       relevant-class P/R/F1, always-relevant floor.
  relevance_clusters.csv               the same metrics aggregated per
                                       applicability_type and per category.
  relevance_gtshare_regression.csv     per-obligation performance regressed on the
                                       GT relevant share (per model + POOLED).
  relevance_metrics_excl_unclear.csv   2-class metrics on the GT != unclear subset.
  relevance_baselines.csv              reference classifiers for Stage 1 AND
                                       Stage 3 (binary + 3-class GT).
  relevance_h3_unclear_avoidance.csv   H3: do models ever predict `unclear`?

Pure analysis, no API calls. Scored rows = both gt_label and pred_label non-empty
(empty pred = parse failure, counted separately). All resampling goes through
lib.bootstrap (Efron percentile, N_BOOTSTRAP replicates, default_rng(GLOBAL_SEED)).

The preds carry a frozen `gt_label` column; the run aborts if it disagrees with
the GT loader, so a changed GT cannot be half-applied (re-run phase4a first).

Run: python -m scripts.eval.phase5_relevance_metrics
"""
from __future__ import annotations

import csv
from collections import Counter

from scripts.eval._common import (
    FULFILLMENT_CLASSES, GEN_MODELS, PREDS, RELEVANCE_CLASSES, RESULTS, write_csv,
)
from scripts.eval._load_gt import gt_master
from scripts.eval.lib import relevance_derived as rd
from scripts.eval.lib.baselines import BASELINE_FIELDS, baseline_rows
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, bootstrap_macro_f1_ci, prf


def read_preds(model_key: str) -> list[dict]:
    path = PREDS / f"relevance_{model_key}.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _gt_rows() -> list[dict]:
    """Stage-1 GT from the loader (company_id, obligation_id, relevance)."""
    g = gt_master()
    return [{"company_id": r.company_id, "obligation_id": r.obligation_id,
             "relevance": r.relevance} for r in g.itertuples(index=False)]


def _check_preds_match_gt(gt_rows: list[dict], preds: dict[str, list[dict]]) -> None:
    """The preds carry a frozen gt_label column; it must equal the current GT."""
    ref = {(r["company_id"], r["obligation_id"]): r["relevance"] for r in gt_rows}
    for model, rows in preds.items():
        bad = [(r["company_id"], r["obligation_id"], r["gt_label"],
                ref.get((r["company_id"], r["obligation_id"]), "<missing>"))
               for r in rows if r["gt_label"] != ref.get((r["company_id"], r["obligation_id"]))]
        if bad:
            raise SystemExit(
                f"{model}: {len(bad)} rows disagree with the GT loader, e.g. {bad[:3]}. "
                "Re-run scripts.eval.phase4a_relevance to re-score the cached predictions.")


def _stage3_baselines() -> list[dict]:
    """Stage-3 references on both fulfillment ground truths, same systematics."""
    ternary = [r.fulfillment for r in gt_master().itertuples(index=False) if r.fulfillment]
    binary = [r.fulfillment for r in gt_master(binary=True).itertuples(index=False) if r.fulfillment]
    return (baseline_rows("stage3_fulfillment_ternary", ternary, FULFILLMENT_CLASSES)
            + baseline_rows("stage3_fulfillment_binary", binary, ["fulfilled", "not_fulfilled"]))


def main() -> None:
    models = [m for m in GEN_MODELS if (PREDS / f"relevance_{m}.csv").exists()]
    if not models:
        raise SystemExit("no relevance_<model>.csv preds found in results/preds/")
    preds = {m: read_preds(m) for m in models}
    scored = {m: [r for r in preds[m] if r["gt_label"] and r["pred_label"]] for m in models}

    gt_rows = _gt_rows()
    _check_preds_match_gt(gt_rows, preds)

    # --- GT distribution + per-obligation GT composition (from the GT, not the preds) ---
    gt_dist = Counter(r["relevance"] for r in gt_rows if r["relevance"])
    total_gt = sum(gt_dist.values())
    write_csv(RESULTS / "gt_label_distribution_relevance.csv",
              [{"class": c, "n": gt_dist.get(c, 0),
                "share": round(gt_dist.get(c, 0) / total_gt, 4) if total_gt else 0.0}
               for c in RELEVANCE_CLASSES],
              ["class", "n", "share"])

    gt_per_req = rd.gt_per_requirement(gt_rows)
    shares = rd.share_relevant_by_obligation(gt_per_req)
    write_csv(RESULTS / "relevance_gt_per_requirement.csv", gt_per_req, rd.GT_PER_REQ_FIELDS)

    metric_rows, conf_rows, perreq_rows, h3_rows, excl_rows = [], [], [], [], []
    for m in models:
        rows, sc = preds[m], scored[m]
        n_parse_fail = sum(1 for r in rows if r["gt_label"] and not r["pred_label"])
        acc, alo, ahi = bootstrap_acc_ci([int(r["pred_label"] == r["gt_label"]) for r in sc])
        macro, mlo, mhi = bootstrap_macro_f1_ci(sc, RELEVANCE_CLASSES)

        row = {"model": m, "model_id": GEN_MODELS[m], "n_scored": len(sc),
               "n_parse_fail": n_parse_fail, "accuracy": round(acc, 4),
               "acc_ci_lo": round(alo, 4), "acc_ci_hi": round(ahi, 4),
               "macro_f1": round(macro, 4),
               "macro_f1_ci_lo": round(mlo, 4), "macro_f1_ci_hi": round(mhi, 4)}
        for c in RELEVANCE_CLASSES:
            p, r, f1, sup = prf(sc, c)
            row[f"precision_{c}"] = round(p, 4)
            row[f"recall_{c}"] = round(r, 4)
            row[f"f1_{c}"] = round(f1, 4)
            row[f"support_{c}"] = sup
        metric_rows.append(row)

        # confusion (long): every gt x pred combination over scored rows
        conf = Counter((r["gt_label"], r["pred_label"]) for r in sc)
        for g in RELEVANCE_CLASSES:
            for p in RELEVANCE_CLASSES:
                conf_rows.append({"model": m, "gt": g, "pred": p, "n": conf.get((g, p), 0)})

        perreq_rows += rd.per_requirement(m, sc, shares)
        excl_rows.append(rd.metrics_excl_unclear(m, sc))

        # H3 — unclear avoidance
        n_pred_unclear = sum(1 for r in sc if r["pred_label"] == "unclear")
        gt_unclear = [r for r in sc if r["gt_label"] == "unclear"]
        gt_unclear_recall = (sum(1 for r in gt_unclear if r["pred_label"] == "unclear")
                             / len(gt_unclear)) if gt_unclear else float("nan")
        h3_rows.append({
            "model": m, "n_scored": len(sc),
            "n_pred_unclear": n_pred_unclear,
            "pred_unclear_rate": round(n_pred_unclear / len(sc), 4) if sc else 0.0,
            "n_gt_unclear": len(gt_unclear),
            "gt_unclear_recall": round(gt_unclear_recall, 4) if gt_unclear else "",
            "unclear_avoidance_rate": round(1 - gt_unclear_recall, 4) if gt_unclear else "",
        })

    metric_fields = (["model", "model_id", "n_scored", "n_parse_fail", "accuracy",
                      "acc_ci_lo", "acc_ci_hi", "macro_f1", "macro_f1_ci_lo", "macro_f1_ci_hi"]
                     + [f"{p}_{c}" for c in RELEVANCE_CLASSES
                        for p in ("precision", "recall", "f1", "support")])
    write_csv(RESULTS / "relevance_metrics_per_model.csv", metric_rows, metric_fields)
    write_csv(RESULTS / "relevance_confusion.csv", conf_rows, ["model", "gt", "pred", "n"])
    write_csv(RESULTS / "relevance_per_requirement.csv", perreq_rows, rd.PER_REQ_FIELDS)
    write_csv(RESULTS / "relevance_clusters.csv", rd.clusters(scored), rd.CLUSTER_FIELDS)
    write_csv(RESULTS / "relevance_gtshare_regression.csv",
              rd.gtshare_regression(perreq_rows, shares), rd.REGRESSION_FIELDS)
    write_csv(RESULTS / "relevance_metrics_excl_unclear.csv", excl_rows, rd.EXCL_UNCLEAR_FIELDS)
    write_csv(RESULTS / "relevance_h3_unclear_avoidance.csv", h3_rows,
              ["model", "n_scored", "n_pred_unclear", "pred_unclear_rate",
               "n_gt_unclear", "gt_unclear_recall", "unclear_avoidance_rate"])

    base = baseline_rows("stage1_relevance", [r["relevance"] for r in gt_rows if r["relevance"]],
                         RELEVANCE_CLASSES) + _stage3_baselines()
    write_csv(RESULTS / "relevance_baselines.csv", base, BASELINE_FIELDS)

    # --- console summary ---
    print(f"models: {models}")
    print("GT relevance dist: " + "  ".join(f"{c}={gt_dist.get(c,0)}" for c in RELEVANCE_CLASSES))
    print(f"\n{'model':18} {'n':>4} {'acc':>6} {'95% CI':>15} {'macroF1':>8} {'95% CI':>15} {'predUnc':>8}")
    for row, h3 in zip(metric_rows, h3_rows):
        print(f"{row['model']:18} {row['n_scored']:>4} "
              f"{row['accuracy']:>6.3f} [{row['acc_ci_lo']:.3f},{row['acc_ci_hi']:.3f}] "
              f"{row['macro_f1']:>8.3f} [{row['macro_f1_ci_lo']:.3f},{row['macro_f1_ci_hi']:.3f}]"
              f" {h3['n_pred_unclear']:>8}")
    print("\nreference classifiers:")
    for b in base:
        print(f"  {b['stage']:28} {b['baseline']:16} acc={b['accuracy']:.4f} "
              f"macroF1={b['macro_f1']:.4f}")
    print(f"\nwrote 10 CSVs to {RESULTS}")


if __name__ == "__main__":
    main()
