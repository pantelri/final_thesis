"""Build DataFrame 1: one row per annotated text span (expected: 232 rows).

Columns: company, region_id, rid, label, category, start, end,
         char_len, word_len, rel_pos, erfuellung, text
"""
from __future__ import annotations
import pandas as pd

_LABEL_SEP = "_"


def _rcode(label_full: str | None) -> str | None:
    if not label_full:
        return None
    return label_full.split(_LABEL_SEP)[0]


def build_spans_df(raw_spans: list[dict], req_map: dict) -> pd.DataFrame:
    rows = []
    for s in raw_spans:
        rc = _rcode(s["label_full"])
        req = req_map.get(rc, {})
        text: str = s["text"]
        char_len = s["end"] - s["start"]
        word_len = len(text.split()) if text else 0
        rel_pos = round(s["start"] / s["char_count"], 4) if s["char_count"] else None

        rows.append({
            "company": s["company"],
            "region_id": s["region_idx"],
            "rid": s["rid"],
            "label": s["label_full"],
            "category": req.get("category"),
            "start": s["start"],
            "end": s["end"],
            "char_len": char_len,
            "word_len": word_len,
            "rel_pos": rel_pos,
            "erfuellung": s["erfuellung"],
            "text": text,
        })

    return pd.DataFrame(rows)
