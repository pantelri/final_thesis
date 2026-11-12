"""Build DataFrame 2: one row per (company × Offenlegungspflicht) = 182 rows.

When two Pflichten are connected by a relation at a company, the text_combined
for each of them is the union of spans from both, sorted by position.
"""
from __future__ import annotations
from itertools import product
import pandas as pd

_DF2_COLS = [
    "company", "label", "rcode", "category", "title_de",
    "n_spans", "erfuellung", "text_combined",
]


def _rcode(label_full: str) -> str:
    return label_full.split("_")[0]


def _union_text(spans_subset: pd.DataFrame) -> str:
    ordered = spans_subset.sort_values("start")
    return " [...] ".join(ordered["text"].tolist())


def _build_partner_map(edge_df: pd.DataFrame) -> dict[tuple[str, str], set[str]]:
    """Map (company, label_full) -> set of partner label_full values via relation edges."""
    partners: dict[tuple[str, str], set[str]] = {}
    for _, row in edge_df.iterrows():
        company, a, b = row["company"], row["label_a"], row["label_b"]
        partners.setdefault((company, a), set()).add(b)
        partners.setdefault((company, b), set()).add(a)
    return partners


def build_pflichten_df(
    spans_df: pd.DataFrame,
    edge_df: pd.DataFrame,
    req_map: dict,
    all_companies: list[str],
    all_labels: list[str],
) -> pd.DataFrame:
    """Produce 14 × 13 = 182 rows (all_companies × all_labels)."""
    partner_map = _build_partner_map(edge_df)

    rows = []
    for company, label in product(sorted(all_companies), sorted(all_labels)):
        rc = _rcode(label)
        req = req_map.get(rc, {})

        base = spans_df[(spans_df["company"] == company) & (spans_df["label"] == label)]

        partner_labels = partner_map.get((company, label), set())
        partner = spans_df[
            (spans_df["company"] == company) & (spans_df["label"].isin(partner_labels))
        ]

        union = pd.concat([base, partner], ignore_index=True)
        text_combined = _union_text(union) if not union.empty else None
        n_spans = len(base)
        erfuellung = base.iloc[0]["erfuellung"] if n_spans > 0 else None

        rows.append({
            "company": company,
            "label": label,
            "rcode": rc,
            "category": req.get("category"),
            "title_de": req.get("title_de"),
            "n_spans": n_spans,
            "erfuellung": erfuellung,
            "text_combined": text_combined,
        })

    return pd.DataFrame(rows, columns=_DF2_COLS)
