"""Inter-annotator agreement — Krippendorff's alpha (nominal) with unit bootstrap.

Pure functions, no DB access, so they are unit-testable. Reliability data are a
list of units; each unit is the list of values the coders assigned to it (None or
missing entries are ignored; units with fewer than two values are not pairable
and drop out, as in Krippendorff's definition).
"""
import random
from collections import Counter
from itertools import permutations


def alpha_nominal(units: list[list]) -> float | None:
    """Krippendorff's alpha for nominal data (any number of coders, missing allowed).

    Returns None when undefined (no pairable values or no variation at all)."""
    o: Counter = Counter()                 # coincidence matrix o[(c, k)]
    for unit in units:
        vals = [v for v in unit if v is not None]
        m = len(vals)
        if m < 2:
            continue
        for a, b in permutations(range(m), 2):
            o[(vals[a], vals[b])] += 1.0 / (m - 1)
    n_c: Counter = Counter()
    for (c, _k), w in o.items():
        n_c[c] += w
    n = sum(n_c.values())
    if n <= 1:
        return None
    d_o = sum(w for (c, k), w in o.items() if c != k)
    d_e = n * n - sum(v * v for v in n_c.values())
    if d_e == 0:
        return None
    return 1.0 - (n - 1) * d_o / d_e


def percent_agreement(units: list[list]) -> float | None:
    """Share of pairable units on which all present values are identical."""
    usable = [[v for v in u if v is not None] for u in units]
    usable = [u for u in usable if len(u) >= 2]
    if not usable:
        return None
    return sum(len(set(u)) == 1 for u in usable) / len(usable)


def n_pairable(units: list[list]) -> int:
    return sum(1 for u in units if sum(v is not None for v in u) >= 2)


def bootstrap_ci(units: list[list], reps: int = 5000, level: float = 0.95,
                 seed: int = 1) -> tuple[float | None, float | None]:
    """Percentile CI for alpha: resample whole units with replacement (Hayes &
    Krippendorff). Replicates where alpha is undefined are skipped."""
    pairable = [u for u in units if sum(v is not None for v in u) >= 2]
    if len(pairable) < 2:
        return None, None
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        a = alpha_nominal([rng.choice(pairable) for _ in pairable])
        if a is not None:
            stats.append(a)
    if not stats:
        return None, None
    stats.sort()
    lo = stats[int((1 - level) / 2 * (len(stats) - 1))]
    hi = stats[int((1 + level) / 2 * (len(stats) - 1))]
    return lo, hi
