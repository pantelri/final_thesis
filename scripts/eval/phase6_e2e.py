"""Phase 6 — end-to-end cumulative correctness + oracle ablation (winners only).

Best-of-breed pipeline on the binary GT:
  Stage 1  relevance   = gemini_3_1_pro      (Phase-4a winner, 0.918)
  Stage 2  retrieval    = gemini/baseSeg/llmdesc/enriched @k=5 (Phase-3 winner)
  Stage 3  fulfillment  = qwen_3_7_max, 2-option prompt (Phase-4b winner)

Population = the 140 applicable pairs (is_applicable=yes → GT relevance 'relevant',
binary fulfillment GT). These are exactly the pairs that traverse all three stages.

Per-pair stage correctness:
  s1  = Stage-1 model predicts 'relevant'   (GT relevance is 'relevant' for all 140)
  s2  = Hit@5: a retrieved top-5 span overlaps a GT evidence span  (correct verdict
        on a wrong span counts as an error — hence Hit@5, not just the verdict)
  s3p = qwen verdict on the PREDICTED top-5 == GT fulfillment
  s3o = qwen verdict on the ORACLE GT spans == GT fulfillment

Cumulative correct (all required stages right) per config:
  full            s1  & s2 & s3p
  oracle_rel      1   & s2 & s3p          (perfect relevance)
  oracle_retr     s1  & 1  & s3o          (perfect retrieval → S3 sees gold evidence)
  oracle_rel_retr 1   & 1  & s3o
  full_oracle     1   & 1  & 1   = 1.0    (degenerate ceiling sanity check)

Ablation deltas (oracle_* − full), paired Efron bootstrap @seed 42, N=1000; a stage
is a significant bottleneck iff its CI excludes 0. Biggest positive delta = bottleneck.

Writes results/e2e_cumulative.csv, results/ablation_configs.csv,
results/ablation_deltas_bootstrap.csv. Retrieval is single-threaded (ChromaDB).
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import RESULTS, PREDS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.clf_metrics import bootstrap_acc_ci, bootstrap_delta_ci
from scripts.eval.lib.evidence import predicted_passages, _oracle_spans

REL_PRED = PREDS / "relevance_gemini_3_1_pro.csv"
FUL_PRED = PREDS / "fulfillmentbin_qwen_3_7_max_predicted_k5_rank.csv"
FUL_ORACLE = PREDS / "fulfillmentbin_qwen_3_7_max_oracle.csv"


def _hit_at_5(company: str, obl: str, oracle: dict) -> int:
    """1 iff a retrieval-winner top-5 span overlaps any GT evidence span for the pair."""
    gold = oracle.get((company, obl), [])
    if not gold:
        return 0
    for (ps, pe, _) in predicted_passages(company, obl, k=5, order="rank"):
        for (gs, ge) in gold:
            if max(ps, gs) < min(pe, ge):   # half-open interval overlap
                return 1
    return 0


def main() -> None:
    gtm = gt_master(binary=True)
    sub = gtm[gtm["fulfillment"] != ""]
    gt = {(r.company_id, r.obligation_id): r.fulfillment for r in sub.itertuples(index=False)}

    relp = {(r.company_id, r.obligation_id): r.pred_label
            for r in pd.read_csv(REL_PRED).itertuples(index=False)}
    s3p = {(r.company_id, r.obligation_id): r.pred_label
           for r in pd.read_csv(FUL_PRED).itertuples(index=False)}
    s3o = {(r.company_id, r.obligation_id): r.pred_label
           for r in pd.read_csv(FUL_ORACLE).itertuples(index=False)}

    pairs = sorted(set(gt) & set(relp) & set(s3p) & set(s3o))
    print(f"e2e population (applicable pairs): {len(pairs)}")

    oracle = _oracle_spans()
    print("computing Hit@5 (single-threaded retrieval)…")
    per = []
    for (c, o) in pairs:
        s1 = int(relp[(c, o)] == "relevant")
        s2 = _hit_at_5(c, o, oracle)
        s3_pred = int(s3p[(c, o)] == gt[(c, o)])
        s3_orac = int(s3o[(c, o)] == gt[(c, o)])
        per.append({"company_id": c, "obligation_id": o, "gt": gt[(c, o)],
                    "s1_relevant": s1, "s2_hit5": s2,
                    "s3_pred_correct": s3_pred, "s3_oracle_correct": s3_orac})
    pf = pd.DataFrame(per)
    pf.to_csv(RESULTS / "e2e_cumulative.csv", index=False)

    configs = {
        "full":            pf.s1_relevant & pf.s2_hit5 & pf.s3_pred_correct,
        "oracle_rel":      1               & pf.s2_hit5 & pf.s3_pred_correct,
        "oracle_retr":     pf.s1_relevant & 1            & pf.s3_oracle_correct,
        "oracle_rel_retr": 1               & 1            & pf.s3_oracle_correct,
        "full_oracle":     pd.Series(1, index=pf.index),
    }

    rows, correct_by_cfg = [], {}
    for name, series in configs.items():
        c = series.astype(int).tolist()
        correct_by_cfg[name] = c
        acc, lo, hi = bootstrap_acc_ci(c)
        rows.append({"config": name, "n": len(c), "cumulative_acc": round(acc, 4),
                     "acc_ci_lo": round(lo, 4), "acc_ci_hi": round(hi, 4),
                     "n_correct": int(sum(c))})
    cfg_df = pd.DataFrame(rows)
    cfg_df.to_csv(RESULTS / "ablation_configs.csv", index=False)

    # stage means (diagnostic): how often each stage is individually right
    print(f"\nstage hit rates: S1 relevant {pf.s1_relevant.mean():.3f} | "
          f"S2 Hit@5 {pf.s2_hit5.mean():.3f} | S3 pred {pf.s3_pred_correct.mean():.3f} | "
          f"S3 oracle {pf.s3_oracle_correct.mean():.3f}")

    deltas = []
    full = correct_by_cfg["full"]
    for name, label in [("oracle_rel", "relevance"), ("oracle_retr", "retrieval"),
                        ("oracle_rel_retr", "relevance+retrieval")]:
        d, lo, hi = bootstrap_delta_ci(correct_by_cfg[name], full)
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        deltas.append({"oracle_config": name, "isolates": label, "vs": "full",
                       "delta": round(d, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                       "significant": sig})
    dd = pd.DataFrame(deltas)
    dd.to_csv(RESULTS / "ablation_deltas_bootstrap.csv", index=False)

    assert correct_by_cfg["full_oracle"] == [1] * len(pairs), "full_oracle must be the ceiling (1.0)"
    bottleneck = max(deltas, key=lambda r: r["delta"])

    print("\n=== cumulative correctness ===")
    print(cfg_df.to_string(index=False))
    print("\n=== ablation deltas vs full (bigger = bigger bottleneck) ===")
    print(dd.to_string(index=False))
    print(f"\nBOTTLENECK: {bottleneck['isolates']} (Δ={bottleneck['delta']:+.4f}, "
          f"CI[{bottleneck['ci_lo']:+.4f},{bottleneck['ci_hi']:+.4f}], sig={bottleneck['significant']})")


if __name__ == "__main__":
    main()
