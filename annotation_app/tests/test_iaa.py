import krippendorff
import numpy as np

from app.iaa import alpha_nominal, bootstrap_ci, percent_agreement

# Krippendorff's reference example (4 coders, 12 units, missing data); nominal alpha = 0.743
DATA = [
    [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
]
UNITS = [list(col) for col in zip(*DATA)]


def test_reference_value():
    assert round(alpha_nominal(UNITS), 3) == 0.743


def test_matches_krippendorff_package_on_random_pairs():
    rng = np.random.default_rng(0)
    for _ in range(20):
        a = rng.integers(0, 3, 60)
        b = np.where(rng.random(60) < 0.7, a, rng.integers(0, 3, 60))
        ref = krippendorff.alpha(reliability_data=np.vstack([a, b]).astype(float),
                                 level_of_measurement="nominal")
        assert abs(alpha_nominal([[int(x), int(y)] for x, y in zip(a, b)]) - ref) < 1e-9


def test_edge_cases_and_ci():
    assert alpha_nominal([["yes", "yes"], ["yes", "yes"]]) is None
    assert percent_agreement([["a", "a"], ["a", "b"], ["a", None]]) == 0.5
    units = [["y", "y"]] * 40 + [["n", "n"]] * 15 + [["y", "n"]] * 5
    lo, hi = bootstrap_ci(units, reps=500)
    assert lo < alpha_nominal(units) < hi
