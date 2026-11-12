"""Entry point: build all three DataFrames from label-studio-gts.json.

Usage
-----
    python main_gt.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from gt_analysis.gt_parser import load_data, load_raw_spans
from gt_analysis.requirements_loader import load_requirements
from gt_analysis.df_spans import build_spans_df
from gt_analysis.relations import resolve_relations
from gt_analysis.df_pflichten import build_pflichten_df
from gt_analysis.df_combinations import build_combinations_df

BASE = Path(__file__).parent
GTS_PATH = BASE / "label-studio-gts.json"
REQ_PATH = BASE / "Requirements" / "offenlegungspflichten_gefiltert.json"


def build_all(
    gts_path: Path = GTS_PATH,
    req_path: Path = REQ_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (df_spans, df_pflichten, df_combinations, relations_df, edge_list_df)."""
    data = load_data(gts_path)
    req_map = load_requirements(req_path)

    raw_spans = load_raw_spans(data)
    df_spans = build_spans_df(raw_spans, req_map)

    rel_df, edge_df = resolve_relations(data)

    all_companies = sorted(df_spans["company"].unique())
    all_labels = sorted(df_spans["label"].dropna().unique())

    df_pflichten = build_pflichten_df(df_spans, edge_df, req_map, all_companies, all_labels)
    df_combinations = build_combinations_df(df_spans, edge_df, all_labels, all_companies)

    return df_spans, df_pflichten, df_combinations, rel_df, edge_df


OUT_DIR = BASE / "gt_output"


def save_csvs(
    df_spans: pd.DataFrame,
    df_pflichten: pd.DataFrame,
    df_combinations: pd.DataFrame,
    rel_df: pd.DataFrame,
    edge_df: pd.DataFrame,
    out_dir: Path = OUT_DIR,
) -> None:
    out_dir.mkdir(exist_ok=True)
    df_spans.to_csv(out_dir / "df1_spans.csv", index=False, encoding="utf-8-sig")
    df_pflichten.to_csv(out_dir / "df2_pflichten.csv", index=False, encoding="utf-8-sig")
    # companies list → semicolon-separated string for CSV compatibility
    df_combinations_export = df_combinations.copy()
    df_combinations_export["companies"] = df_combinations_export["companies"].apply(
        lambda lst: "; ".join(lst)
    )
    df_combinations_export.to_csv(out_dir / "df3_kombinationen.csv", index=False, encoding="utf-8-sig")
    rel_df.to_csv(out_dir / "relations_gerichtet.csv", index=False, encoding="utf-8-sig")
    edge_df.to_csv(out_dir / "relations_kanten.csv", index=False, encoding="utf-8-sig")
    print(f"CSVs gespeichert in: {out_dir.resolve()}")


if __name__ == "__main__":
    df1, df2, df3, rel_df, edge_df = build_all()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    print(f"=== DataFrame 1: Spans ({len(df1)} rows) ===")
    print(df1[["company", "region_id", "label", "start", "end", "erfuellung"]].head(10).to_string())

    print(f"\n=== DataFrame 2: Pflichten je Firma ({len(df2)} rows) ===")
    print(df2[["company", "label", "n_spans", "erfuellung"]].head(20).to_string())

    print(f"\n=== DataFrame 3: Kombinationen ({len(df3)} rows) ===")
    print(df3[df3["n_companies"] > 0][["label_a", "label_b", "n_companies", "companies"]].to_string())

    print(f"\n=== Relations ({len(rel_df)} rows, gerichtet) ===")
    print(rel_df.to_string())

    print(f"\n=== Edge List ({len(edge_df)} rows, ungerichtet dedupliziert) ===")
    print(edge_df.to_string())

    save_csvs(df1, df2, df3, rel_df, edge_df)
