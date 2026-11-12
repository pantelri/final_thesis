"""Load the frozen retrieval GT snapshot into eval structures.

Retrieval eval set = (company, obligation) pairs that carry RELEVANT evidence
(is_relevant == 't'); their GT spans (md char offsets) are the positives. Pairs
without relevant evidence are excluded (recall undefined).
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

import pandas as pd

from scripts.eval._common import RESULTS

GT_SNAPSHOT = RESULTS / "retrieval_gt_snapshot.csv"


@lru_cache(maxsize=1)
def gt_positives() -> dict[tuple[str, str], list[tuple[int, int]]]:
    """(company, obligation) -> [(char_start, char_end), ...] for is_relevant pairs."""
    df = pd.read_csv(GT_SNAPSHOT, dtype=str, keep_default_na=False)
    df = df[df["is_relevant"] == "t"]
    out: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for r in df.itertuples(index=False):
        if r.char_start == "" or r.char_end == "":
            continue
        out[(r.company_id, r.obligation_id)].append((int(float(r.char_start)), int(float(r.char_end))))
    return dict(out)


@lru_cache(maxsize=1)
def gt_source_text() -> dict[tuple[str, str], str]:
    """(company, obligation) -> concatenated GT evidence text (one/two-shot queries)."""
    df = pd.read_csv(GT_SNAPSHOT, dtype=str, keep_default_na=False)
    df = df[df["is_relevant"] == "t"]
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in df.itertuples(index=False):
        out[(r.company_id, r.obligation_id)].append(r.text)
    return {k: " ".join(v).strip() for k, v in out.items()}


def companies_with_gt(obl_id: str) -> list[str]:
    return sorted(c for (c, o) in gt_positives() if o == obl_id)


def eval_pairs() -> list[tuple[str, str]]:
    return sorted(gt_positives().keys())
