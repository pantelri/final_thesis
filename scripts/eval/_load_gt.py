"""Load the frozen DB-export CSVs (results/_db_export/) as pandas frames.

These are the host-side view of the canonical Postgres GT, extracted via
`docker exec psql \\copy` (host psycopg2 segfaults under this Anaconda build).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.eval._common import RESULTS

EXPORT = RESULTS / "_db_export"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(EXPORT / name, dtype=str, keep_default_na=False, na_values=[])


def load_items() -> pd.DataFrame:
    df = _read("annotation_items.csv")
    df["passage_start"] = pd.to_numeric(df["passage_start"], errors="coerce")
    df["passage_end"] = pd.to_numeric(df["passage_end"], errors="coerce")
    return df


def load_annotations(binary: bool = False) -> pd.DataFrame:
    """Annotation labels. binary=True uses the 2-class fulfillment GT
    (annotations_binary.csv, 2026-06-30 relabeling) instead of the original
    3-class export."""
    return _read("annotations_binary.csv" if binary else "annotations.csv")


def load_sentences() -> pd.DataFrame:
    df = _read("passage_sentences.csv")
    df["idx"] = pd.to_numeric(df["idx"], errors="coerce").astype("Int64")
    return df


def load_irrelevant() -> pd.DataFrame:
    return _read("irrelevant_elements.csv")


def load_suggested() -> pd.DataFrame:
    return _read("suggested_passages.csv")


def load_obligations() -> pd.DataFrame:
    return _read("obligations.csv")


def load_companies() -> pd.DataFrame:
    return _read("companies.csv")


def gt_master(binary: bool = False) -> pd.DataFrame:
    """One row per (company, obligation) item with joined annotation labels + thesis mappings.

    binary=True uses the 2-class fulfillment GT (yes/no only); the FULFILLMENT_MAP
    still applies (partially absent from the data)."""
    from scripts.eval._common import RELEVANCE_MAP, FULFILLMENT_MAP

    items = load_items().rename(columns={"id": "item_id"})
    ann = load_annotations(binary=binary)
    m = items.merge(ann, on="item_id", how="left", validate="one_to_one")
    m["relevance"] = m["is_applicable"].map(RELEVANCE_MAP)
    m["fulfillment"] = m["is_fulfilled"].map(lambda v: FULFILLMENT_MAP.get(v, "") if v else "")
    return m
