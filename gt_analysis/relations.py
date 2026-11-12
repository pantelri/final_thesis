"""Map Label Studio relation entries to span labels.

Public API
----------
resolve_relations(data) -> (relations_df, edge_list_df)

relations_df  : company, from_label, to_label, direction
edge_list_df  : company, label_a, label_b  (undirected, deduplicated)
"""
from __future__ import annotations
import pandas as pd

_REL_COLS = ["company", "from_label", "to_label", "direction"]
_EDGE_COLS = ["company", "label_a", "label_b"]


def resolve_relations(data: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treat relations as undirected couplings; return both directed and deduplicated forms."""
    rid_to_label: dict[tuple[str, str], str] = {}
    for task in data:
        company: str = task["data"]["company"]
        ann = task["annotations"][0]
        for r in ann["result"]:
            if r["type"] == "labels":
                lbl = r["value"]["labels"][0] if r["value"]["labels"] else None
                if lbl:
                    rid_to_label[(company, r["id"])] = lbl

    rel_rows: list[dict] = []
    for task in data:
        company = task["data"]["company"]
        ann = task["annotations"][0]
        for r in ann["result"]:
            if r["type"] == "relation":
                from_lbl = rid_to_label.get((company, r["from_id"]))
                to_lbl = rid_to_label.get((company, r["to_id"]))
                if from_lbl and to_lbl:
                    rel_rows.append({
                        "company": company,
                        "from_label": from_lbl,
                        "to_label": to_lbl,
                        "direction": r.get("direction", "right"),
                    })

    rel_df = (
        pd.DataFrame(rel_rows, columns=_REL_COLS)
        if rel_rows
        else pd.DataFrame(columns=_REL_COLS)
    )

    edges: set[tuple[str, str, str]] = set()
    for _, row in rel_df.iterrows():
        a, b = row["from_label"], row["to_label"]
        edges.add((row["company"], min(a, b), max(a, b)))

    edge_df = pd.DataFrame(sorted(edges), columns=_EDGE_COLS)
    return rel_df, edge_df
