"""Derived Stage-1 (relevance) analyses beyond plain accuracy.

Row builders for the CSVs written by `phase5_relevance_metrics`. Two sources:

  ground truth  `_load_gt.gt_master()` / `_consensus_gt.consensus_gt()` — the
                per-obligation GT composition is computed from the GT itself, not
                from a model's `gt_label` column, so it stays valid even if a
                prediction file is stale.
  predictions   `results/preds/relevance_<model>.csv` (cached, no API calls).

Obligation metadata (category, applicability_type) comes from
`Requirements/offenlegungspflichten_gefiltert.csv` via `lib.obligations`.

Convention for undefined metrics: an empty cell, which pandas reads back as NaN.
Macro-F1 is undefined for a slice whose ground truth holds a single class; the
degenerate value would otherwise be read as a performance figure.
"""
from __future__ import annotations

from collections import defaultdict

from scripts.eval._common import RELEVANCE_CLASSES
from scripts.eval.lib.clf_metrics import (
    bootstrap_macro_f1_ci, gt_classes, macro_f1, pred_classes, prf,
)
from scripts.eval.lib.obligations import CLUSTER_KEYS, meta_of

BINARY_CLASSES = ["relevant", "not_relevant"]

GT_PER_REQ_FIELDS = [
    "obligation_id", "n", "n_relevant", "n_not_relevant", "n_unclear",
    "share_relevant", "share_not_relevant", "share_unclear",
    "category", "applicability_type",
]
PER_REQ_FIELDS = [
    "model", "obligation_id", "n", "accuracy", "macro_f1", "n_gt_classes",
    "f1_relevant", "precision_relevant", "recall_relevant", "always_relevant_baseline",
]
CLUSTER_FIELDS = [
    "cluster_key", "cluster", "model", "n_obligations", "n", "gt_relevant_share",
    "accuracy", "macro_f1", "f1_relevant", "f1_not_relevant",
    "precision_relevant", "recall_relevant", "precision_not_relevant",
    "recall_not_relevant", "gt_classes",
]
REGRESSION_FIELDS = [
    "model", "target", "n", "pearson_r", "pearson_p", "spearman_rho", "spearman_p",
    "slope", "intercept", "r_squared", "slope_stderr",
]
EXCL_UNCLEAR_FIELDS = [
    "model", "n", "accuracy", "macro_f1_2cls", "macro_f1_2cls_ci_lo",
    "macro_f1_2cls_ci_hi", "f1_relevant", "f1_not_relevant", "n_pred_unclear_in_subset",
]


def _r(x, nd: int = 4):
    """Round for CSV output; undefined values become an empty cell (-> NaN)."""
    if x is None or x != x:  # NaN
        return ""
    return round(float(x), nd)


def _accuracy(scored: list[dict]) -> float:
    return sum(1 for r in scored if r["pred_label"] == r["gt_label"]) / len(scored)


# ------------------------------------------------------------------ 1. GT ----
def gt_per_requirement(gt_rows: list[dict]) -> list[dict]:
    """Per-obligation GT composition. `gt_rows` = dicts with obligation_id + relevance."""
    by_obl: dict[str, list[str]] = defaultdict(list)
    for r in gt_rows:
        if r["relevance"]:
            by_obl[r["obligation_id"]].append(r["relevance"])
    out = []
    for oid in sorted(by_obl):
        labels = by_obl[oid]
        n = len(labels)
        counts = {c: labels.count(c) for c in RELEVANCE_CLASSES}
        meta = meta_of(oid)
        out.append({
            "obligation_id": oid, "n": n,
            **{f"n_{c}": counts[c] for c in RELEVANCE_CLASSES},
            **{f"share_{c}": _r(counts[c] / n) for c in RELEVANCE_CLASSES},
            "category": meta["category"], "applicability_type": meta["applicability_type"],
        })
    return out


def share_relevant_by_obligation(gt_per_req: list[dict]) -> dict[str, float]:
    return {r["obligation_id"]: float(r["share_relevant"]) for r in gt_per_req}


# ------------------------------------------------- 2. per-obligation metrics ----
def per_requirement(model: str, scored: list[dict], shares: dict[str, float]) -> list[dict]:
    """Per (model, obligation): accuracy plus F-measures.

    macro_f1 averages the classes present in the GT *or* the predictions of that
    obligation, and is left undefined when the GT holds a single class (true for
    all obligations except R12, R22, R23, R24).
    """
    by_obl: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        by_obl[r["obligation_id"]].append(r)
    out = []
    for oid in sorted(by_obl):
        rows = by_obl[oid]
        in_gt = gt_classes(rows, RELEVANCE_CLASSES)
        present = sorted(set(in_gt) | set(pred_classes(rows, RELEVANCE_CLASSES)),
                         key=RELEVANCE_CLASSES.index)
        p, r, f1, _sup = prf(rows, "relevant")
        out.append({
            "model": model, "obligation_id": oid, "n": len(rows),
            "accuracy": _r(_accuracy(rows)),
            "macro_f1": _r(macro_f1(rows, present)) if len(in_gt) > 1 else "",
            "n_gt_classes": len(in_gt),
            "f1_relevant": _r(f1), "precision_relevant": _r(p), "recall_relevant": _r(r),
            "always_relevant_baseline": _r(shares.get(oid, float("nan"))),
        })
    return out


# --------------------------------------------------------- 3. cluster rows ----
def _cluster_row(cluster_key: str, cluster: str, model: str, rows: list[dict]) -> dict:
    in_gt = gt_classes(rows, RELEVANCE_CLASSES)
    has_neg = "not_relevant" in in_gt
    p_rel, r_rel, f1_rel, _ = prf(rows, "relevant")
    p_neg, r_neg, f1_neg, _ = prf(rows, "not_relevant")
    return {
        "cluster_key": cluster_key, "cluster": cluster, "model": model,
        "n_obligations": len({r["obligation_id"] for r in rows}), "n": len(rows),
        "gt_relevant_share": _r(sum(1 for r in rows if r["gt_label"] == "relevant") / len(rows)),
        "accuracy": _r(_accuracy(rows)),
        # macro over the classes the CLUSTER's ground truth actually contains
        "macro_f1": _r(macro_f1(rows, in_gt)),
        "f1_relevant": _r(f1_rel),
        "f1_not_relevant": _r(f1_neg) if has_neg else "",
        "precision_relevant": _r(p_rel), "recall_relevant": _r(r_rel),
        "precision_not_relevant": _r(p_neg) if has_neg else "",
        "recall_not_relevant": _r(r_neg) if has_neg else "",
        "gt_classes": "|".join(in_gt),
    }


def clusters(preds_by_model: dict[str, list[dict]]) -> list[dict]:
    """One row per cluster_key x cluster x model, for every key in CLUSTER_KEYS."""
    out = []
    for key in CLUSTER_KEYS:
        buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for model, scored in preds_by_model.items():
            for r in scored:
                buckets[(meta_of(r["obligation_id"])[key], model)].append(r)
        for (cluster, model) in sorted(buckets):
            out.append(_cluster_row(key, cluster, model, buckets[(cluster, model)]))
    return out


# ------------------------------------------------------------ 4. regression ----
def _fit(xs: list[float], ys: list[float], model: str, target: str) -> dict:
    from scipy import stats
    row = {"model": model, "target": target, "n": len(xs)}
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return row | {f: "" for f in REGRESSION_FIELDS[3:]}
    r, p = stats.pearsonr(xs, ys)
    rho, prho = stats.spearmanr(xs, ys)
    ls = stats.linregress(xs, ys)
    return row | {
        "pearson_r": _r(r), "pearson_p": _r(p, 6),
        "spearman_rho": _r(rho), "spearman_p": _r(prho, 6),
        "slope": _r(ls.slope), "intercept": _r(ls.intercept),
        "r_squared": _r(ls.rvalue ** 2), "slope_stderr": _r(ls.stderr),
    }


def gtshare_regression(per_req_rows: list[dict], shares: dict[str, float],
                       targets=("accuracy", "macro_f1")) -> list[dict]:
    """OLS + correlations of per-obligation performance on the GT relevant share.

    One row per model x target plus a POOLED row over all model-obligation cells.
    Cells whose target is undefined (macro-F1 on single-GT-class obligations) are
    dropped, so the macro-F1 rows rest on fewer points than the accuracy rows —
    `n` states how many.
    """
    out = []
    models = sorted({r["model"] for r in per_req_rows})
    for target in targets:
        for model in models:
            pts = [(shares[r["obligation_id"]], float(r[target]))
                   for r in per_req_rows if r["model"] == model and r[target] != ""]
            out.append(_fit([x for x, _ in pts], [y for _, y in pts], model, target))
        pooled = [(shares[r["obligation_id"]], float(r[target]))
                  for r in per_req_rows if r[target] != ""]
        out.append(_fit([x for x, _ in pooled], [y for _, y in pooled], "POOLED", target))
    return out


# ------------------------------------------------------- 5. unclear excluded ----
def metrics_excl_unclear(model: str, scored: list[dict]) -> dict:
    """Two-class metrics on the GT != unclear subset (178 items).

    Predictions of `unclear` stay in the subset and stay wrong — dropping them
    would credit the models for abstaining on items that are in fact decidable.
    """
    sub = [r for r in scored if r["gt_label"] != "unclear"]
    pt, lo, hi = bootstrap_macro_f1_ci(sub, BINARY_CLASSES)
    return {
        "model": model, "n": len(sub), "accuracy": _r(_accuracy(sub)),
        "macro_f1_2cls": _r(pt), "macro_f1_2cls_ci_lo": _r(lo), "macro_f1_2cls_ci_hi": _r(hi),
        "f1_relevant": _r(prf(sub, "relevant")[2]),
        "f1_not_relevant": _r(prf(sub, "not_relevant")[2]),
        "n_pred_unclear_in_subset": sum(1 for r in sub if r["pred_label"] == "unclear"),
    }
