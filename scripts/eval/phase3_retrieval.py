"""Phase 3 — stage-isolated retrieval experiment (no generation).

Factorial: 2 embeddings x 2 segmentations x 4 query variants, evaluated at
k in {1,3,5,7} (retrieve top-7 once, truncate). Metrics vs the canonical
retrieval GT snapshot (span-overlap).

Query variants:
  enriched  : retrieval_text from the enriched obligation JSON.
  zeroshot  : obligation title + verification criterion (description only).
  oneshot   : another company's GT evidence for the same obligation (leave-one-out
              over every other source company; mean+/-std; source != target).
  twoshot   : two other companies' GT evidence concatenated (fixed-seed sampling,
              capped per target; NA if <2 other sources).

Outputs (results/):
  retrieval_metrics.csv, recall_at_k_curve.csv, retrieval_main_effects.csv,
  retrieval_per_requirement.csv  (+ winner recorded to run_manifest via Phase 8).

Run: python -m scripts.eval.phase3_retrieval
"""
from __future__ import annotations

import itertools
import random
from statistics import mean, pstdev

import pandas as pd

from scripts.eval._common import COLLECTIONS, GLOBAL_SEED, RESULTS, write_csv
from scripts.eval.lib.chroma import retrieve
from scripts.eval.lib.embedder import QueryEmbedder
from scripts.eval.lib.gt import (
    companies_with_gt, eval_pairs, gt_positives, gt_source_text,
)
from scripts.eval.lib.metrics import metrics_at_k
from scripts.eval.lib.queries import query_enriched, query_zeroshot

KS = [1, 3, 5, 7]
TOP_K = 7
TWO_SHOT_CAP = 5          # max source-pairs sampled per target (determinism via seed)
OPERATING_K = 5           # winner operating point (aligns with verification-k)
METRIC_KEYS = ["recall", "hit", "precision", "rr"]


def _embedders() -> dict[str, QueryEmbedder]:
    return {ek: QueryEmbedder(ek) for ek in {v.embed for v in COLLECTIONS.values()}}


def _avg(dicts: list[dict]) -> dict:
    return {m: mean(d[m] for d in dicts) for m in METRIC_KEYS} if dicts else {m: float("nan") for m in METRIC_KEYS}


def run_pair(coll_key, embed_key, variant, target, obl, qe, spans, rng):
    """Return {k: metrics_dict} for one eval pair, averaged over sources where applicable."""
    out = {k: None for k in KS}

    def eval_query(text):
        vec = qe.embed(text)
        retrieved = retrieve(coll_key, vec, target, TOP_K)
        return {k: metrics_at_k(retrieved, spans, k) for k in KS}

    if variant == "enriched":
        return eval_query(query_enriched(obl))
    if variant == "zeroshot":
        return eval_query(query_zeroshot(obl))

    sources = [c for c in companies_with_gt(obl) if c != target]
    if variant == "oneshot":
        if not sources:
            return {k: None for k in KS}
        per_src = [eval_query(gt_source_text()[(s, obl)]) for s in sources]
        return {k: _avg([ps[k] for ps in per_src]) for k in KS}

    if variant == "twoshot":
        if len(sources) < 2:
            return {k: None for k in KS}      # NA
        all_pairs = list(itertools.combinations(sorted(sources), 2))
        rng.shuffle(all_pairs)
        chosen = all_pairs[:TWO_SHOT_CAP]
        per_pair = []
        for s1, s2 in chosen:
            text = (gt_source_text()[(s1, obl)] + "\n\n" + gt_source_text()[(s2, obl)]).strip()
            per_pair.append(eval_query(text))
        return {k: _avg([pp[k] for pp in per_pair]) for k in KS}
    raise ValueError(variant)


def main() -> None:
    embedders = _embedders()
    pairs = eval_pairs()
    pos = gt_positives()
    print(f"eval pairs (is_relevant=t): {len(pairs)}")

    variants = ["enriched", "zeroshot", "oneshot", "twoshot"]
    # per-pair records: one row per (coll, variant, pair, k)
    records: list[dict] = []
    for coll_key, spec in COLLECTIONS.items():
        embed_key = spec.embed
        qe = embedders[embed_key]
        for variant in variants:
            rng = random.Random(GLOBAL_SEED)      # reset per (coll,variant) for determinism
            n_na = 0
            for (company, obl) in pairs:
                res = run_pair(coll_key, embed_key, variant, company, obl, qe, pos[(company, obl)], rng)
                for k in KS:
                    if res[k] is None:
                        n_na += 1 if k == KS[0] else 0
                        continue
                    records.append({
                        "embedding": embed_key, "segmentation": spec.seg,
                        "table_rep": spec.table_rep, "collection": coll_key,
                        "query_variant": variant, "company": company, "obligation": obl,
                        "k": k, **res[k],
                    })
            print(f"  {coll_key:28} {variant:9} done  (NA pairs: {n_na})")

    df = pd.DataFrame(records)
    df.to_csv(RESULTS / "retrieval_per_pair.csv", index=False, encoding="utf-8")

    # ---- aggregate: retrieval_metrics.csv ----
    GROUP = ["embedding", "segmentation", "table_rep", "query_variant"]
    agg = (df.groupby(GROUP + ["k"])
             .agg(n_pairs=("recall", "size"),
                  recall_mean=("recall", "mean"), recall_std=("recall", "std"),
                  hit_mean=("hit", "mean"),
                  precision_mean=("precision", "mean"),
                  mrr_mean=("rr", "mean"))
             .reset_index().sort_values(GROUP + ["k"]))
    for c in ["recall_mean", "recall_std", "hit_mean", "precision_mean", "mrr_mean"]:
        agg[c] = agg[c].round(4)
    agg.to_csv(RESULTS / "retrieval_metrics.csv", index=False, encoding="utf-8")

    # ---- recall_at_k_curve.csv (recall + hit vs k) ----
    curve = agg[GROUP + ["k", "recall_mean", "hit_mean"]]
    curve.to_csv(RESULTS / "recall_at_k_curve.csv", index=False, encoding="utf-8")

    # ---- winner by Recall@OPERATING_K ----
    op = agg[agg["k"] == OPERATING_K].sort_values("recall_mean", ascending=False)
    win = op.iloc[0]
    winner = dict(embedding=win["embedding"], segmentation=win["segmentation"],
                  table_rep=win["table_rep"], query_variant=win["query_variant"],
                  k=int(OPERATING_K), recall=float(win["recall_mean"]),
                  hit=float(win["hit_mean"]), mrr=float(win["mrr_mean"]))
    write_csv(RESULTS / "retrieval_winner.csv", [winner],
              ["embedding", "segmentation", "table_rep", "query_variant", "k", "recall", "hit", "mrr"])

    # ---- main effects (marginal Recall@OPERATING_K) ----
    base = df[df["k"] == OPERATING_K]
    eff_rows = []
    for factor in ["embedding", "segmentation", "table_rep"]:
        for level, g in base.groupby(factor):
            eff_rows.append({"factor": factor, "level": level, "recall_mean": round(g["recall"].mean(), 4)})
    for (emb, seg, trep), g in base.groupby(["embedding", "segmentation", "table_rep"]):
        eff_rows.append({"factor": "interaction", "level": f"{emb}|{seg}|{trep}",
                         "recall_mean": round(g["recall"].mean(), 4)})
    write_csv(RESULTS / "retrieval_main_effects.csv", eff_rows, ["factor", "level", "recall_mean"])

    # ---- per-requirement for the winning config ----
    w = df[(df["embedding"] == winner["embedding"]) & (df["segmentation"] == winner["segmentation"])
           & (df["table_rep"] == winner["table_rep"])
           & (df["query_variant"] == winner["query_variant"]) & (df["k"] == OPERATING_K)]
    pr = (w.groupby("obligation")
            .agg(n_pairs=("recall", "size"), recall_mean=("recall", "mean"),
                 hit_mean=("hit", "mean"), mrr_mean=("rr", "mean"))
            .reset_index().sort_values("recall_mean"))
    for c in ["recall_mean", "hit_mean", "mrr_mean"]:
        pr[c] = pr[c].round(4)
    pr.to_csv(RESULTS / "retrieval_per_requirement.csv", index=False, encoding="utf-8")

    # ---- console summary ----
    print("\n" + "=" * 78)
    print(f"Phase 3 — retrieval metrics @k={OPERATING_K} (sorted by Recall)")
    print("=" * 78)
    show = op[["embedding", "segmentation", "table_rep", "query_variant", "recall_mean",
               "hit_mean", "precision_mean", "mrr_mean"]].to_string(index=False)
    print(show)
    print("-" * 78)
    print(f"WINNER @k={OPERATING_K}: {winner['embedding']} / {winner['segmentation']} / "
          f"{winner['table_rep']} / {winner['query_variant']}  "
          f"Recall={winner['recall']:.3f} Hit={winner['hit']:.3f} MRR={winner['mrr']:.3f}")
    print(f"  outputs: retrieval_metrics.csv, recall_at_k_curve.csv, retrieval_main_effects.csv,")
    print(f"           retrieval_per_requirement.csv, retrieval_winner.csv, retrieval_per_pair.csv")


if __name__ == "__main__":
    main()
