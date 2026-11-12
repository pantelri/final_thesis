"""Single source of truth for the Efron percentile bootstrap.

Every phase resamples through this module so that the same quantity always gets
the same interval (METHODS_NOTES 4.5: phases previously produced slightly
different bounds for the same statistic because they seeded different RNGs).

Fixed here and nowhere else:
  generator  numpy.random.default_rng(GLOBAL_SEED), re-created at the start of
             every call, so a call's interval never depends on call order.
  replicates N_BOOTSTRAP (1000), drawn one at a time as `rng.integers(0, n, n)`.
  interval   2.5 / 97.5 percentiles of the replicate distribution.

Paired comparisons resample the *item index* once per replicate and evaluate both
arms on the same resample (`bootstrap_paired_delta_ci`).
"""
from __future__ import annotations

from typing import Callable, Iterator, Sequence

import numpy as np

from scripts.eval._common import GLOBAL_SEED, N_BOOTSTRAP

CI_LO_PCT, CI_HI_PCT = 2.5, 97.5
NAN3 = (float("nan"), float("nan"), float("nan"))


def rng(seed: int = GLOBAL_SEED) -> np.random.Generator:
    """The canonical generator. Use this instead of np.random.* anywhere."""
    return np.random.default_rng(seed)


def boot_indices(n: int, n_boot: int = N_BOOTSTRAP,
                 seed: int = GLOBAL_SEED) -> Iterator[np.ndarray]:
    """Yield `n_boot` Efron resamples of the item indices 0..n-1."""
    g = rng(seed)
    for _ in range(n_boot):
        yield g.integers(0, n, n)


def percentile_ci(values: Sequence[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    return float(np.percentile(arr, CI_LO_PCT)), float(np.percentile(arr, CI_HI_PCT))


def bootstrap_mean_ci(values, n_boot: int = N_BOOTSTRAP,
                      seed: int = GLOBAL_SEED) -> tuple[float, float, float]:
    """Mean of `values` + 95% percentile CI (accuracy = mean of a 0/1 vector)."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return NAN3
    means = [arr[idx].mean() for idx in boot_indices(arr.size, n_boot, seed)]
    return (float(arr.mean()), *percentile_ci(means))


def bootstrap_paired_delta_ci(a, b, n_boot: int = N_BOOTSTRAP,
                              seed: int = GLOBAL_SEED) -> tuple[float, float, float]:
    """mean(a) - mean(b) + 95% CI. `a` and `b` must be aligned over the same items;
    each replicate resamples the item index once and scores both arms on it."""
    aa, bb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if aa.size == 0 or aa.size != bb.size:
        return NAN3
    deltas = [aa[idx].mean() - bb[idx].mean() for idx in boot_indices(aa.size, n_boot, seed)]
    return (float(aa.mean() - bb.mean()), *percentile_ci(deltas))


def bootstrap_stat_ci(items: Sequence, stat: Callable[[list], float],
                      n_boot: int = N_BOOTSTRAP,
                      seed: int = GLOBAL_SEED) -> tuple[float, float, float]:
    """Point value of `stat(items)` + 95% CI, resampling the items themselves.

    For statistics that are not means of per-item scores (F1, F-beta, macro-F1):
    `items` is any sequence (rows, (gt, pred) tuples), `stat` maps a resampled
    list to a scalar.
    """
    seq = list(items)
    if not seq:
        return NAN3
    vals = [stat([seq[i] for i in idx]) for idx in boot_indices(len(seq), n_boot, seed)]
    return (float(stat(seq)), *percentile_ci(vals))
