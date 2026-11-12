"""Phase 5 / RQ5 — does evidence passage POSITION matter for fulfillment?

Winning config only (qwen_3_7_max / predicted / statute_only, 2-option output),
scored on the binary GT (140 pairs). Four arms:

  k5_rank         top-5, most-relevant FIRST (retrieval order) — baseline
  k1_rank         single passage (top-1) — ranked-list vs single-passage
  k5_doc          top-5, source-document order
  k5_relevancelast top-5, most-relevant LAST (U-shaped-attention exploit)

Per-arm accuracy + macro-F1 (+ bootstrap CI), and paired bootstrap deltas of each
variant vs the k5_rank baseline (significant iff CI excludes 0). Pure analysis, no API.

Writes results/rq5_passage_ordering.csv and results/rq5_ordering_deltas.csv.
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import RESULTS, PREDS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, bootstrap_delta_ci, prf

ARMS = ["k5_rank", "k1_rank", "k5_doc", "k5_relevancelast"]
BASELINE = "k5_rank"
CLASSES = ["fulfilled", "not_fulfilled"]


def _load(arm: str) -> dict:
    f = PREDS / f"fulfillmentbin_qwen_3_7_max_predicted_{arm}.csv"
    return {(r.company_id, r.obligation_id): r.pred_label for r in pd.read_csv(f).itertuples(index=False)}


def main() -> None:
    gtm = gt_master(binary=True)
    gt = {(r.company_id, r.obligation_id): r.fulfillment
          for r in gtm[gtm["fulfillment"] != ""].itertuples(index=False)}
    preds = {arm: _load(arm) for arm in ARMS}

    pairs = sorted(set(gt).intersection(*[set(p) for p in preds.values()]))
    print(f"aligned pairs: {len(pairs)}")

    scored = {arm: [{"pred_label": preds[arm][k], "gt_label": gt[k],
                     "correct": int(preds[arm][k] == gt[k])} for k in pairs]
              for arm in ARMS}

    table = []
    for arm in ARMS:
        sc = scored[arm]
        acc, lo, hi = bootstrap_acc_ci([r["correct"] for r in sc])
        macro = sum(prf(sc, c)[2] for c in CLASSES) / len(CLASSES)
        nfail = sum(1 for r in sc if not isinstance(r["pred_label"], str) or not r["pred_label"])
        row = {"arm": arm, "n": len(sc), "accuracy": round(acc, 4),
               "acc_ci_lo": round(lo, 4), "acc_ci_hi": round(hi, 4),
               "macro_f1": round(macro, 4), "parse_fail": nfail}
        for c in CLASSES:
            p, r, f1, sup = prf(sc, c)
            row |= {f"f1_{c}": round(f1, 4), f"recall_{c}": round(r, 4), f"support_{c}": sup}
        table.append(row)

    out = RESULTS / "rq5_passage_ordering.csv"
    pd.DataFrame(table).to_csv(out, index=False)

    base = [r["correct"] for r in scored[BASELINE]]
    deltas = []
    for arm in ARMS:
        if arm == BASELINE:
            continue
        d, lo, hi = bootstrap_delta_ci([r["correct"] for r in scored[arm]], base)
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        deltas.append({"arm": arm, "vs": BASELINE, "n": len(pairs), "delta": round(d, 4),
                       "ci_lo": round(lo, 4), "ci_hi": round(hi, 4), "significant": sig})
    dout = RESULTS / "rq5_ordering_deltas.csv"
    pd.DataFrame(deltas).to_csv(dout, index=False)

    print(f"Wrote {out}\nWrote {dout}\n")
    print(pd.DataFrame(table)[["arm", "n", "accuracy", "acc_ci_lo", "acc_ci_hi",
                               "macro_f1", "recall_fulfilled", "recall_not_fulfilled"]].to_string(index=False))
    print("\ndeltas vs k5_rank (+= variant better):")
    print(pd.DataFrame(deltas).to_string(index=False))


if __name__ == "__main__":
    main()
