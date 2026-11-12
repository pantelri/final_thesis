"""Tests for the GT analysis pipeline.

Run with:  python -m pytest tests_gt.py -v
"""
from __future__ import annotations
from pathlib import Path
import pytest
import pandas as pd

from main_gt import build_all

BASE = Path(__file__).parent
GTS_PATH = BASE / "label-studio-gts.json"
REQ_PATH = BASE / "Requirements" / "offenlegungspflichten_gefiltert.json"


@pytest.fixture(scope="module")
def all_dfs():
    return build_all(GTS_PATH, REQ_PATH)


# ── DataFrame 1 ─────────────────────────────────────────────────────────────

def test_span_count(all_dfs):
    df1, *_ = all_dfs
    assert len(df1) == 232, f"Expected 232 spans, got {len(df1)}"


def test_no_missing_erfuellung(all_dfs):
    df1, *_ = all_dfs
    missing = df1["erfuellung"].isna().sum()
    assert missing == 0, f"{missing} span(s) have no erfuellung value"


def test_no_missing_label(all_dfs):
    df1, *_ = all_dfs
    assert df1["label"].notna().all(), "Some spans have no label"


def test_duplicate_offsets_resolved_by_rid(all_dfs):
    """7 cases share identical (company, start, end) — they must have distinct rids."""
    df1, *_ = all_dfs
    dup_mask = df1.duplicated(subset=["company", "start", "end"], keep=False)
    dups = df1[dup_mask]
    assert len(dups) == 14, f"Expected 14 duplicate-offset rows (7 pairs), got {len(dups)}"
    assert dups["rid"].nunique() == 14, "Duplicate-offset spans must have unique rids"


# ── DataFrame 2 ─────────────────────────────────────────────────────────────

def test_pflichten_df_shape(all_dfs):
    _, df2, *_ = all_dfs
    assert len(df2) == 182, f"Expected 182 rows (14 × 13), got {len(df2)}"


def test_pflichten_all_companies_present(all_dfs):
    _, df2, *_ = all_dfs
    assert df2["company"].nunique() == 14


def test_pflichten_all_labels_present(all_dfs):
    _, df2, *_ = all_dfs
    assert df2["label"].nunique() == 13


def test_relation_expansion_htg(all_dfs):
    """HTG_2024: R04 ↔ R17 relation — both rows should include union text."""
    df1, df2, df3, rel_df, edge_df = all_dfs
    r04 = df2[(df2["company"] == "HTG_2024") & df2["label"].str.startswith("R04")]
    r17 = df2[(df2["company"] == "HTG_2024") & df2["label"].str.startswith("R17")]
    assert len(r04) == 1 and len(r17) == 1
    assert r04.iloc[0]["text_combined"] is not None
    assert r17.iloc[0]["text_combined"] is not None
    # Union means the combined text of R04 should contain R17 span text (or vice versa)
    r04_span_text = df1[(df1["company"] == "HTG_2024") & df1["label"].str.startswith("R04")].iloc[0]["text"]
    r17_span_text = df1[(df1["company"] == "HTG_2024") & df1["label"].str.startswith("R17")].iloc[0]["text"]
    assert r04_span_text[:30] in r17.iloc[0]["text_combined"] or r17_span_text[:30] in r04.iloc[0]["text_combined"]


# ── DataFrame 3 ─────────────────────────────────────────────────────────────

def test_combinations_shape(all_dfs):
    _, _, df3, _, _ = all_dfs
    assert len(df3) == 78, f"Expected C(13,2)=78 pairs, got {len(df3)}"


def test_combinations_known_overlap(all_dfs):
    """Amazon_2024 has R04/R17 at identical offsets → they must appear in DF3."""
    _, _, df3, _, _ = all_dfs
    row = df3[
        (df3["label_a"].str.startswith("R04") & df3["label_b"].str.startswith("R17")) |
        (df3["label_a"].str.startswith("R17") & df3["label_b"].str.startswith("R04"))
    ]
    assert len(row) == 1
    assert "Amazon_2024" in row.iloc[0]["companies"]


# ── Relations ────────────────────────────────────────────────────────────────

def test_edge_list_deduplicated(all_dfs):
    """HTG_2024 has a bidirectional annotation — the edge list must have only 1 row for it."""
    _, _, _, _, edge_df = all_dfs
    htg_edges = edge_df[edge_df["company"] == "HTG_2024"]
    assert len(htg_edges) == 1, f"Expected 1 edge for HTG_2024, got {len(htg_edges)}"


def test_edge_list_total(all_dfs):
    """Total undirected edges across all companies."""
    _, _, _, _, edge_df = all_dfs
    assert len(edge_df) == 7, f"Expected 7 edges, got {len(edge_df)}"
