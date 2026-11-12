"""Phase 5 — does a 2-option fulfillment prompt beat the 3-option one?

Compares, on the SAME binary GT (140 pairs, 122 fulfilled / 18 not_fulfilled;
majority baseline 0.871), for the winning config qwen_3_7_max / predicted@5 / statute_only:

  * binary       : the 2-option run (fulfillmentbin_..._predicted_k5_rank), prompted
                   with only fulfilled/not_fulfilled.
  * ternary→A    : the original 3-option run, collapsed partially→not_fulfilled
                   (conservative completeness rule).
  * ternary→B    : the original 3-option run, collapsed partially→fulfilled
                   (matches how the human relabeling leaned).

Paired bootstrap delta (binary − each ternary collapse) tells us whether forcing the
model into 2 options actually helps. Pure analysis, no API.

Writes results/fulfillment_binary_vs_ternary.csv.
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import RESULTS, PREDS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, bootstrap_delta_ci, prf

BINARY = PREDS / "fulfillmentbin_qwen_3_7_max_predicted_k5_rank.csv"
TERNARY = PREDS / "fulfillment_qwen_3_7_max_predicted_statute_only.csv"
COLLAPSE = {"A_partially_to_not_fulfilled": {"partially": "not_fulfilled"},
            "B_partially_to_fulfilled": {"partially": "fulfilled"}}
CLASSES = ["fulfilled", "not_fulfilled"]


def _macro_f1(scored: list[dict]) -> float:
    return sum(prf(scored, c)[2] for c in CLASSES) / len(CLASSES)


def _row(name: str, scored: list[dict]) -> dict:
    correct = [r["correct"] for r in scored]
    acc, lo, hi = bootstrap_acc_ci(correct)
    out = {"arm": name, "n": len(scored), "accuracy": round(acc, 4),
           "acc_ci_lo": round(lo, 4), "acc_ci_hi": round(hi, 4),
           "macro_f1": round(_macro_f1(scored), 4)}
    for c in CLASSES:
        p, r, f1, sup = prf(scored, c)
        out |= {f"f1_{c}": round(f1, 4), f"recall_{c}": round(r, 4), f"support_{c}": sup}
    return out


def main() -> None:
    gtm = gt_master(binary=True)
    gt = {(r.company_id, r.obligation_id): r.fulfillment
          for r in gtm[gtm["fulfillment"] != ""].itertuples(index=False)}

    binp = {(r.company_id, r.obligation_id): r.pred_label
            for r in pd.read_csv(BINARY).itertuples(index=False)}
    terp = {(r.company_id, r.obligation_id): r.pred_label
            for r in pd.read_csv(TERNARY).itertuples(index=False)}

    pairs = sorted(set(gt) & set(binp) & set(terp))  # aligned population for paired tests
    print(f"aligned pairs: {len(pairs)}  (binary GT)")

    def scored(predmap, collapse=None):
        rows = []
        for key in pairs:
            pred = predmap[key]
            if collapse and pred in collapse:
                pred = collapse[pred]
            rows.append({"pred_label": pred, "gt_label": gt[key],
                         "correct": int(pred == gt[key])})
        return rows

    arms = {"binary": scored(binp)}
    for name, rule in COLLAPSE.items():
        arms[f"ternary_{name}"] = scored(terp, rule)

    table = [_row(name, sc) for name, sc in arms.items()]
    # majority baseline on this population
    maj = max(sum(1 for k in pairs if gt[k] == c) for c in CLASSES) / len(pairs)
    table.append({"arm": "majority_baseline", "n": len(pairs), "accuracy": round(maj, 4)})

    df = pd.DataFrame(table)
    out = RESULTS / "fulfillment_binary_vs_ternary.csv"
    df.to_csv(out, index=False)

    # paired deltas: binary vs each ternary collapse
    print("\nbinary vs ternary (paired bootstrap delta, +=binary better):")
    bin_correct = [r["correct"] for r in arms["binary"]]
    deltas = []
    for name in COLLAPSE:
        ter_correct = [r["correct"] for r in arms[f"ternary_{name}"]]
        d, lo, hi = bootstrap_delta_ci(bin_correct, ter_correct)
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        deltas.append({"comparison": f"binary_minus_ternary_{name}", "n": len(pairs),
                       "delta": round(d, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                       "significant": sig})
        print(f"  binary − ternary[{name}]: Δ={d:+.4f}  CI[{lo:+.4f},{hi:+.4f}]  sig={sig}")
    dout = RESULTS / "fulfillment_binary_vs_ternary_delta.csv"
    pd.DataFrame(deltas).to_csv(dout, index=False)

    print(f"\nWrote {out}\nWrote {dout}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
