"""Stage-3 verification context variants (H2).

Each obligation is described to the verifier in one of two ways:
  statute_only : legal basis + verification criterion (the bare regulatory text).
  web_enriched : an LLM/web-synthesised explanatory description
                 (Requirements/offenlegungspflichten_web_enriched.json).

context(obl_id, variant) -> (title_de, context_block).
"""
from __future__ import annotations

import json
from functools import lru_cache

from scripts.eval._common import ENRICHED_JSON, ROOT

WEB_ENRICHED_JSON = ROOT / "Requirements" / "offenlegungspflichten_web_enriched.json"
CONTEXT_VARIANTS = ["statute_only", "web_enriched"]


@lru_cache(maxsize=1)
def _enriched() -> dict[str, dict]:
    data = json.loads(ENRICHED_JSON.read_text(encoding="utf-8"))["requirements"]
    return {o["id"]: o for o in data}


@lru_cache(maxsize=1)
def _web() -> dict[str, dict]:
    return json.loads(WEB_ENRICHED_JSON.read_text(encoding="utf-8"))


def context(obl_id: str, variant: str) -> tuple[str, str]:
    o = _enriched()[obl_id]
    title = o.get("title_de", "")
    if variant == "statute_only":
        block = (f"Rechtsgrundlage: {o.get('legal_basis', '')}\n"
                 f"Prüfkriterium: {o.get('verification_criterion', '')}")
        return title, block.strip()
    if variant == "web_enriched":
        w = _web().get(obl_id, {})
        return title, (w.get("web_enriched_text", "") or "").strip()
    raise ValueError(f"unknown context variant {variant!r}")
