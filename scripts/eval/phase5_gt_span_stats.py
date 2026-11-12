"""Phase 5 — descriptive statistics of the ground-truth evidence spans.

Pure analysis, no API. Reads the frozen GT span snapshot
(`results/retrieval_gt_snapshot.csv`) and writes `results/gt_span_stats.csv`:
one row per scope (the overall retrieval eval set + one row per obligation),
describing how many evidence elements each relevant pair carries, their length,
their sentence/table mix, and how they were located (exact vs envelope fallback).

Eval population = the retrieval eval set (is_relevant=true). CONFIRMED 170 pairs.
"""
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parents[2] / "results"
SNAPSHOT = RESULTS / "retrieval_gt_snapshot.csv"
OUT = RESULTS / "gt_span_stats.csv"


def _stats(df: pd.DataFrame, scope: str) -> dict:
    per_pair = df.groupby("item_id")
    spans_per_pair = per_pair.size()
    chars_per_pair = per_pair["n_chars"].sum()
    is_table = df["element_type"].eq("table")
    # exact + multi are genuinely located char spans; envelope_fallback is the
    # item char-envelope backstop used where the verbatim text wasn't relocatable.
    located = df["span_status"].isin(["exact", "multi"])
    return {
        "scope": scope,
        "n_pairs": df["item_id"].nunique(),
        "n_span_elements": len(df),
        "spans_per_pair_mean": round(spans_per_pair.mean(), 3),
        "spans_per_pair_median": float(spans_per_pair.median()),
        "spans_per_pair_min": int(spans_per_pair.min()),
        "spans_per_pair_max": int(spans_per_pair.max()),
        "chars_per_span_mean": round(df["n_chars"].mean(), 1),
        "chars_per_span_median": float(df["n_chars"].median()),
        "chars_per_span_max": int(df["n_chars"].max()),
        "chars_per_pair_mean": round(chars_per_pair.mean(), 1),
        "n_sentence_elements": int((~is_table).sum()),
        "n_table_elements": int(is_table.sum()),
        "pct_table": round(100 * is_table.mean(), 1),
        "n_located": int(located.sum()),
        "n_fallback": int((~located).sum()),
        "pct_located": round(100 * located.mean(), 1),
    }


def main() -> None:
    df = pd.read_csv(SNAPSHOT)
    # Retrieval eval set: only spans of relevant pairs carry validated evidence.
    # is_relevant is exported as a Postgres bool string ('t'/'f').
    rel = df["is_relevant"].astype(str).str.strip().str.lower()
    df = df[rel.isin(["t", "true", "1"])].copy()

    rows = [_stats(df, "ALL")]
    for ob, g in df.groupby("obligation_id"):
        rows.append(_stats(g, ob))

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    overall = rows[0]
    print(f"Wrote {OUT}")
    print(f"  pairs={overall['n_pairs']}  span_elements={overall['n_span_elements']}  "
          f"spans/pair={overall['spans_per_pair_mean']}  "
          f"chars/span median={overall['chars_per_span_median']}  "
          f"table={overall['pct_table']}%  located={overall['pct_located']}%")


if __name__ == "__main__":
    main()
