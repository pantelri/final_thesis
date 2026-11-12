"""Reference classifiers — the floor every model result is read against.

Three references, each scored against a ground-truth label vector:

  always_majority  constant prediction of the most frequent GT class.
                   Deterministic, so no interval is reported.
  random_prior     i.i.d. draws from the GT class priors.
  random_uniform   i.i.d. uniform draws over the class vocabulary.

The random references are averaged over N_DRAWS draws from a fresh
`lib.bootstrap.rng()` (numpy.random.default_rng(GLOBAL_SEED)) per reference, so a
reference's value does not depend on which other references were computed first.
Their interval is the 2.5/97.5 percentile of macro-F1 across those draws — the
spread of the reference itself, not a sampling CI on a point estimate.

Macro-F1 averages over the full class vocabulary passed in (zero-denominator
classes contribute 0), so it is comparable to the models' macro-F1 on the same
stage.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from scripts.eval.lib.bootstrap import percentile_ci, rng

N_DRAWS = 10_000
BASELINE_FIELDS = ["stage", "baseline", "accuracy", "macro_f1",
                   "macro_f1_ci_lo", "macro_f1_ci_hi", "n", "detail"]


def _macro_f1_idx(gt: np.ndarray, pred: np.ndarray, n_classes: int) -> float:
    """Macro-F1 over class indices 0..n_classes-1 (matches clf_metrics.macro_f1)."""
    f1 = np.empty(n_classes)
    for c in range(n_classes):
        pc, gc = pred == c, gt == c
        tp = int(np.count_nonzero(pc & gc))
        n_pred, n_gt = int(np.count_nonzero(pc)), int(np.count_nonzero(gc))
        p = tp / n_pred if n_pred else 0.0
        r = tp / n_gt if n_gt else 0.0
        f1[c] = 2 * p * r / (p + r) if (p + r) else 0.0
    return float(f1.mean())


def baseline_rows(stage: str, gt_labels: list[str], classes: list[str],
                  n_draws: int = N_DRAWS) -> list[dict]:
    """One row per reference classifier for a single stage / ground truth."""
    classes = list(classes)
    n_cls = len(classes)
    gt = np.array([classes.index(g) for g in gt_labels])
    n = gt.size
    counts = Counter(gt_labels)
    majority = max(range(n_cls), key=lambda c: counts.get(classes[c], 0))
    priors = np.array([counts.get(c, 0) / n for c in classes], dtype=float)

    const = np.full(n, majority)
    rows = [{
        "stage": stage, "baseline": "always_majority",
        "accuracy": round(float(np.mean(gt == const)), 4),
        "macro_f1": round(_macro_f1_idx(gt, const, n_cls), 4),
        "macro_f1_ci_lo": "", "macro_f1_ci_hi": "", "n": n,
        "detail": f"constant '{classes[majority]}'; deterministic, no interval",
    }]

    for name, p in [("random_prior", priors),
                    ("random_uniform", np.full(n_cls, 1 / n_cls))]:
        g = rng()
        accs, f1s = np.empty(n_draws), np.empty(n_draws)
        for i in range(n_draws):
            draw = g.choice(n_cls, size=n, p=p)
            accs[i] = np.mean(gt == draw)
            f1s[i] = _macro_f1_idx(gt, draw, n_cls)
        lo, hi = percentile_ci(f1s)
        rows.append({
            "stage": stage, "baseline": name,
            "accuracy": round(float(accs.mean()), 4),
            "macro_f1": round(float(f1s.mean()), 4),
            "macro_f1_ci_lo": round(lo, 4), "macro_f1_ci_hi": round(hi, 4), "n": n,
            "detail": f"mean over {n_draws} draws; p=" + "/".join(f"{x:.3f}" for x in p),
        })
    return rows
