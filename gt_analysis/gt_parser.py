"""Load raw span and relation data from a Label Studio JSON export."""
from __future__ import annotations
import json
from pathlib import Path


def load_data(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_raw_spans(data: list[dict]) -> list[dict]:
    """Return a flat list of span dicts, one per labelled region.

    erfuellung is matched to its label by shared region-id (rid), NOT by
    (start, end) — there are 7 cases where two labels share identical offsets.
    region_idx is a 1-based rank by start-offset within each company's spans.
    """
    rows: list[dict] = []
    for task in data:
        company: str = task["data"]["company"]
        char_count: int = task["data"].get("char_count") or len(task["data"].get("text", ""))

        ann = task["annotations"][0]
        results: list[dict] = ann["result"]

        labels_by_rid: dict[str, dict] = {}
        choices_by_rid: dict[str, dict] = {}
        for r in results:
            if r["type"] == "labels":
                labels_by_rid[r["id"]] = r
            elif r["type"] == "choices":
                choices_by_rid[r["id"]] = r

        sorted_labels = sorted(labels_by_rid.values(), key=lambda r: r["value"]["start"])

        for region_idx, lr in enumerate(sorted_labels, start=1):
            rid = lr["id"]
            val = lr["value"]
            choice_val = choices_by_rid.get(rid, {}).get("value", {})
            choices = choice_val.get("choices", [])

            rows.append({
                "company": company,
                "rid": rid,
                "region_idx": region_idx,
                "start": val["start"],
                "end": val["end"],
                "text": val.get("text", ""),
                "label_full": val["labels"][0] if val["labels"] else None,
                "erfuellung": choices[0] if choices else None,
                "char_count": char_count,
            })

    return rows


def load_relations_raw(data: list[dict]) -> list[dict]:
    """Return raw relation entries enriched with company context."""
    rows: list[dict] = []
    for task in data:
        company: str = task["data"]["company"]
        ann = task["annotations"][0]
        for r in ann["result"]:
            if r["type"] == "relation":
                rows.append({
                    "company": company,
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "direction": r.get("direction", "right"),
                })
    return rows
