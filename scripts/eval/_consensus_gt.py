"""Consensus GT loader — strict-majority GT per item from the (multi-annotator) export.

Reuses annotation_app.app.consensus.majority_gt (single source of the majority rule).
On the current single-annotator data this reproduces _load_gt.gt_master exactly; once
several annotators exist it yields the majority-vote GT for re-running the experiments.

Drop-in for gt_master: emits company_id, obligation_id, is_applicable, is_fulfilled,
relevance, fulfillment (+ n_votes, plus per-question consensus flags via unresolved()).

Run as a module to print a parity check against gt_master:
    python -m scripts.eval._consensus_gt
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from annotation_app.app.consensus import majority_gt, needs_more, unresolved_questions
from scripts.eval._common import FULFILLMENT_MAP, RELEVANCE_MAP
from scripts.eval._load_gt import load_annotations, load_items

_BOOL = {"t": "yes", "f": "no", "true": "yes", "false": "no"}


def _vote(row) -> dict:
    isr = str(row.is_relevant).lower() if row.is_relevant else ""
    return {
        "is_relevant": _BOOL.get(isr),
        "length_judgment": row.length_judgment or None,
        "is_applicable": row.is_applicable or None,
        "is_fulfilled": row.is_fulfilled or None,
    }


def votes_by_item() -> dict[str, list[dict]]:
    by_item: dict[str, list[dict]] = defaultdict(list)
    for r in load_annotations().itertuples(index=False):
        by_item[r.item_id].append(_vote(r))
    return dict(by_item)


def consensus_gt() -> pd.DataFrame:
    items = load_items().rename(columns={"id": "item_id"})
    by_item = votes_by_item()
    rows = []
    for it in items.itertuples(index=False):
        votes = by_item.get(it.item_id, [])
        gt = majority_gt(votes)
        appl, fulf = gt["is_applicable"], gt["is_fulfilled"]
        rows.append({
            "item_id": it.item_id, "company_id": it.company_id, "obligation_id": it.obligation_id,
            "is_applicable": appl or "", "is_fulfilled": fulf or "",
            "relevance": RELEVANCE_MAP.get(appl, "") if appl else "",
            "fulfillment": FULFILLMENT_MAP.get(fulf, "") if fulf else "",
            "n_votes": len(votes),
            "unresolved": ",".join(unresolved_questions(votes)),
            "needs_more": needs_more(votes),
        })
    return pd.DataFrame(rows)


def main() -> None:
    from scripts.eval._load_gt import gt_master
    cg = consensus_gt().set_index(["company_id", "obligation_id"])
    gm = gt_master().set_index(["company_id", "obligation_id"])
    rel_mismatch = (cg["relevance"] != gm["relevance"]).sum()
    fulf_mismatch = (cg["fulfillment"] != gm["fulfillment"]).sum()
    print(f"items: {len(cg)}  votes/item: {sorted(cg['n_votes'].unique())}")
    print(f"relevance mismatches vs gt_master:   {rel_mismatch}")
    print(f"fulfillment mismatches vs gt_master: {fulf_mismatch}")
    print(f"items still needing votes: {int(cg['needs_more'].sum())}  "
          f"with unresolved questions: {int((cg['unresolved'] != '').sum())}")
    if rel_mismatch == 0 and fulf_mismatch == 0:
        print("PARITY OK — consensus GT reproduces gt_master on current data.")


if __name__ == "__main__":
    main()
