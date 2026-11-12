"""Classification metric helpers. All resampling goes through lib.bootstrap
(Efron percentile, N_BOOTSTRAP replicates, numpy.random.default_rng(GLOBAL_SEED)).

  prf(scored, cls)               per-class precision/recall/F1/support.
  fbeta(p, r, beta)              F-beta from precision/recall.
  prf_beta(scored, cls, beta)    per-class precision/recall/F_beta/support.
  macro_f1(scored, classes)      unweighted F1 mean over `classes` (NaN if empty).
  gt_classes(scored, classes)    classes with support > 0, in `classes` order.
  pred_classes(scored, classes)  classes that appear as a prediction.

  bootstrap_acc_ci(correct)      mean accuracy + 95% CI.
  bootstrap_delta_ci(a, b)       paired delta mean(a)-mean(b) + 95% CI; a,b are
                                 0/1 lists aligned over the SAME items. The
                                 difference is significant iff the CI excludes 0.
  bootstrap_fbeta_ci(scored, cls, beta)   F_beta + 95% CI (resamples items).
  bootstrap_macro_f1_ci(scored, classes)  macro-F1 + 95% CI (resamples items).

`scored` is a list of dicts carrying at least "gt_label" and "pred_label".
"""
from __future__ import annotations

import numpy as np

from scripts.eval.lib.bootstrap import (
    bootstrap_mean_ci, bootstrap_paired_delta_ci, bootstrap_stat_ci,
)


def bootstrap_acc_ci(correct) -> tuple[float, float, float]:
    return bootstrap_mean_ci([float(c) for c in correct])


def bootstrap_delta_ci(a, b) -> tuple[float, float, float]:
    return bootstrap_paired_delta_ci([float(x) for x in a], [float(x) for x in b])


def prf(scored: list[dict], cls: str) -> tuple[float, float, float, int]:
    tp = sum(1 for r in scored if r["pred_label"] == cls and r["gt_label"] == cls)
    fp = sum(1 for r in scored if r["pred_label"] == cls and r["gt_label"] != cls)
    fn = sum(1 for r in scored if r["pred_label"] != cls and r["gt_label"] == cls)
    support = sum(1 for r in scored if r["gt_label"] == cls)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1, support


def fbeta(p: float, r: float, beta: float) -> float:
    """F_beta. beta>1 weights recall over precision (F2: recall 4x precision)."""
    b2 = beta * beta
    denom = b2 * p + r
    return (1 + b2) * p * r / denom if denom else 0.0


def prf_beta(scored: list[dict], cls: str, beta: float) -> tuple[float, float, float, int]:
    p, r, _f1, sup = prf(scored, cls)
    return p, r, fbeta(p, r, beta), sup


def macro_f1(scored: list[dict], classes) -> float:
    """Unweighted mean F1 over `classes`. Which classes to average over is the
    caller's decision (all label classes / the ones present in the GT / ...);
    zero-denominator classes contribute 0, as in sklearn's zero_division=0."""
    classes = list(classes)
    if not classes:
        return float("nan")
    return float(np.mean([prf(scored, c)[2] for c in classes]))


def gt_classes(scored: list[dict], classes) -> list[str]:
    """Classes from `classes` that actually occur in the ground truth of `scored`."""
    present = {r["gt_label"] for r in scored}
    return [c for c in classes if c in present]


def pred_classes(scored: list[dict], classes) -> list[str]:
    present = {r["pred_label"] for r in scored}
    return [c for c in classes if c in present]


def bootstrap_fbeta_ci(scored: list[dict], cls: str, beta: float) -> tuple[float, float, float]:
    """Point F_beta for class `cls` + 95% percentile CI by resampling items."""
    return bootstrap_stat_ci(scored, lambda rows: prf_beta(rows, cls, beta)[2])


def bootstrap_macro_f1_ci(scored: list[dict], classes) -> tuple[float, float, float]:
    """Point macro-F1 over `classes` + 95% percentile CI by resampling items.

    The class set is held fixed across replicates (it is a property of the metric
    definition, not of the resample), so the interval is comparable across models.
    """
    classes = list(classes)
    return bootstrap_stat_ci(scored, lambda rows: macro_f1(rows, classes))
