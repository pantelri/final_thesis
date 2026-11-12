"""Build DataFrame 3: Zusammengehörigkeit for every pair of Pflichten.

A pair (label_a, label_b) is 'zusammengehörig' at a company when:
 - A relation edge directly connects them there, OR
 - Any span of label_a overlaps (partially, fully, or by containment)
   with any span of label_b.

Columns: label_a, label_b, rcode_a, rcode_b, n_companies, companies
"""
from __future__ import annotations
from itertools import combinations
import pandas as pd


def _any_overlap(
    starts_a: list[int], ends_a: list[int],
    starts_b: list[int], ends_b: list[int],
) -> bool:
    for sa, ea in zip(starts_a, ends_a):
        for sb, eb in zip(starts_b, ends_b):
            if sa < eb and sb < ea:
                return True
    return False


def _build_edge_set(edge_df: pd.DataFrame) -> set[tuple[str, str, str]]:
    return {(row["company"], row["label_a"], row["label_b"]) for _, row in edge_df.iterrows()}


def build_combinations_df(
    spans_df: pd.DataFrame,
    edge_df: pd.DataFrame,
    all_labels: list[str],
    all_companies: list[str],
) -> pd.DataFrame:
    edge_set = _build_edge_set(edge_df)
    label_pairs = list(combinations(sorted(all_labels), 2))

    rows = []
    for label_a, label_b in label_pairs:
        key_a, key_b = min(label_a, label_b), max(label_a, label_b)

        linked_companies: list[str] = []
        for company in sorted(all_companies):
            if (company, key_a, key_b) in edge_set:
                linked_companies.append(company)
                continue

            a_spans = spans_df[(spans_df["company"] == company) & (spans_df["label"] == label_a)]
            b_spans = spans_df[(spans_df["company"] == company) & (spans_df["label"] == label_b)]

            if not a_spans.empty and not b_spans.empty and _any_overlap(
                a_spans["start"].tolist(), a_spans["end"].tolist(),
                b_spans["start"].tolist(), b_spans["end"].tolist(),
            ):
                linked_companies.append(company)

        rows.append({
            "label_a": label_a,
            "label_b": label_b,
            "rcode_a": label_a.split("_")[0],
            "rcode_b": label_b.split("_")[0],
            "n_companies": len(linked_companies),
            "companies": linked_companies,
        })

    return pd.DataFrame(rows)
