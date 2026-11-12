"""Obligation metadata from `Requirements/offenlegungspflichten_gefiltert.csv`.

That CSV is the canonical obligation catalogue (semicolon-separated, utf-8-sig).
It supplies the two cluster keys used in the Stage-1 analyses:

  category           thematic block (LB Forecast Report, HGB Annex §§284-285, ...)
  applicability_type always | conditional | balance_sheet_item
"""
from __future__ import annotations

import csv
from functools import lru_cache

from scripts.eval._common import ROOT

OBLIGATIONS_CSV = ROOT / "Requirements" / "offenlegungspflichten_gefiltert.csv"
CLUSTER_KEYS = ["applicability_type", "category"]
FIELDS = ["title_de", "title_en", "legal_basis", "category", "applicability_type"]


@lru_cache(maxsize=1)
def obligation_meta() -> dict[str, dict[str, str]]:
    """obligation_id -> {title_en, category, applicability_type, ...}."""
    with open(OBLIGATIONS_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    return {r["id"]: {f: (r.get(f) or "") for f in FIELDS} for r in rows}


def meta_of(obligation_id: str) -> dict[str, str]:
    """Metadata for one obligation; empty strings for ids missing from the catalogue."""
    return obligation_meta().get(obligation_id, {f: "" for f in FIELDS})
