"""Build retrieval query strings from the enriched obligations JSON.

enriched : retrieval_text (LLM-synthesized example compliant passage).
zeroshot : obligation title + verification criterion (description only, no example).
(one/two-shot queries are built from GT evidence in phase3_retrieval.)
"""
from __future__ import annotations

import json
from functools import lru_cache

from scripts.eval._common import ENRICHED_JSON


@lru_cache(maxsize=1)
def obligations() -> dict[str, dict]:
    data = json.loads(ENRICHED_JSON.read_text(encoding="utf-8"))["requirements"]
    return {o["id"]: o for o in data}


def query_enriched(obl_id: str) -> str:
    return obligations()[obl_id]["retrieval_text"].strip()


def query_zeroshot(obl_id: str) -> str:
    """Obligation description only: title + verification criterion (no example text)."""
    o = obligations()[obl_id]
    return f"{o['title_de']}. {o.get('verification_criterion', '')}".strip()
