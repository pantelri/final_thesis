"""Analyse Span-Längen (DF1) und Tabellenhäufigkeit je Pflicht (DF2).

Outputs (in gt_output/):
  stats_df1_spans.csv       — char_len / word_len wide-format: gesamt + je Label + je Firma
  stats_span_lengths.csv    — char_len / word_len long-format (legacy)
  stats_tables_per_pflicht.csv — Tabellenzählung je Label aus text_combined
"""
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

BASE = Path(__file__).parent
OUT = BASE / "gt_output"


# ── Tabellenerkennung ─────────────────────────────────────────────────────────

def _count_tables(text: str) -> int:
    """Count contiguous blocks of pipe-lines (≥2 lines) = one markdown table.

    Texts from the JSON export contain literal backslash-n (two chars), not real newlines.
    """
    if not text:
        return 0
    lines = text.split(r"\n")
    in_table = False
    table_line_count = 0
    tables = 0
    for line in lines:
        is_pipe = line.strip().startswith("|") or line.strip().startswith("||")
        if is_pipe:
            in_table = True
            table_line_count += 1
        else:
            if in_table and table_line_count >= 2:
                tables += 1
            in_table = False
            table_line_count = 0
    if in_table and table_line_count >= 2:
        tables += 1
    return tables


# ── Analyse 1: Span-Längen ────────────────────────────────────────────────────

def analyze_span_lengths(df1: pd.DataFrame) -> pd.DataFrame:
    percentiles = [0.50, 0.75, 0.90]
    rows = []

    for metric in ("char_len", "word_len"):
        s = df1[metric]
        row: dict = {"metric": metric}
        row["mean"]   = round(s.mean(), 1)
        row["median"] = round(s.median(), 1)
        for p in percentiles:
            row[f"p{int(p*100)}"] = round(s.quantile(p), 1)
        rows.append(row)

    # Zusätzlich: nach Label aggregiert
    label_rows = []
    for (label,), grp in df1.groupby(["label"]):
        for metric in ("char_len", "word_len"):
            s = grp[metric]
            row = {"label": label, "metric": metric, "n": len(grp)}
            row["mean"]   = round(s.mean(), 1)
            row["median"] = round(s.median(), 1)
            for p in percentiles:
                row[f"p{int(p*100)}"] = round(s.quantile(p), 1)
            label_rows.append(row)

    overall_df = pd.DataFrame(rows)
    by_label_df = pd.DataFrame(label_rows)
    return overall_df, by_label_df


# ── Analyse 1b: Wide-Format-Tabelle für df1 ──────────────────────────────────

def _stats_row(group: pd.DataFrame, group_col: str, group_val: str) -> dict:
    """Compute stats for both char_len and word_len in a single wide row."""
    row: dict = {group_col: group_val, "n_spans": len(group)}
    for metric, prefix in (("char_len", "char"), ("word_len", "words")):
        s = group[metric]
        row[f"{prefix}_mean"]   = round(s.mean(), 1)
        row[f"{prefix}_median"] = round(s.median(), 1)
        row[f"{prefix}_p50"]    = round(s.quantile(0.50), 1)
        row[f"{prefix}_p75"]    = round(s.quantile(0.75), 1)
        row[f"{prefix}_p90"]    = round(s.quantile(0.90), 1)
    return row


def build_df1_stats_wide(df1: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return three wide-format DataFrames: overall, by_label, by_company."""
    overall = pd.DataFrame([_stats_row(df1, "group", "GESAMT")])

    by_label = pd.DataFrame(
        [_stats_row(grp, "label", lbl) for lbl, grp in df1.groupby("label")]
    )

    by_company = pd.DataFrame(
        [_stats_row(grp, "company", comp) for comp, grp in df1.groupby("company")]
    )

    return overall, by_label, by_company


# ── Analyse 2: Tabellen je Pflicht ───────────────────────────────────────────

def analyze_tables_per_pflicht(df2: pd.DataFrame) -> pd.DataFrame:
    df = df2.copy()
    df["n_tables"] = df["text_combined"].fillna("").apply(_count_tables)

    agg = (
        df.groupby(["label", "rcode", "category", "title_de"])
        .agg(
            n_firmen_gesamt=("company", "count"),
            n_firmen_mit_tabelle=("n_tables", lambda x: (x > 0).sum()),
            n_tabellen_gesamt=("n_tables", "sum"),
            n_tabellen_max=("n_tables", "max"),
            n_tabellen_mean=("n_tables", "mean"),
        )
        .reset_index()
    )
    agg["n_tabellen_mean"] = agg["n_tabellen_mean"].round(2)
    return agg.sort_values("label")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df1 = pd.read_csv(OUT / "df1_spans.csv")
    df2 = pd.read_csv(OUT / "df2_pflichten.csv")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    # ── DF1 Wide Stats ────────────────────────────────────────────────────────
    overall_w, by_label_w, by_company_w = build_df1_stats_wide(df1)

    print("=== DF1 Span-Längen: gesamt ===")
    print(overall_w.to_string(index=False))
    print("\n=== DF1 Span-Längen: je Label ===")
    print(by_label_w.to_string(index=False))
    print("\n=== DF1 Span-Längen: je Firma ===")
    print(by_company_w.to_string(index=False))

    df1_stats = pd.concat(
        [overall_w.rename(columns={"group": "gruppe"}),
         by_label_w.rename(columns={"label": "gruppe"}),
         by_company_w.rename(columns={"company": "gruppe"})],
        ignore_index=True,
    )
    df1_stats.insert(1, "typ", (
        ["gesamt"] * len(overall_w) +
        ["label"] * len(by_label_w) +
        ["firma"] * len(by_company_w)
    ))
    df1_stats.to_csv(OUT / "stats_df1_spans.csv", index=False, encoding="utf-8-sig")
    print(f"\nGespeichert: {OUT / 'stats_df1_spans.csv'}")

    # ── Tabellen je Pflicht ───────────────────────────────────────────────────
    tables_df = analyze_tables_per_pflicht(df2)
    print("\n=== Tabellen je Pflicht ===")
    print(tables_df.to_string(index=False))
    tables_df.to_csv(OUT / "stats_tables_per_pflicht.csv", index=False, encoding="utf-8-sig")
    print(f"Gespeichert: {OUT / 'stats_tables_per_pflicht.csv'}")
