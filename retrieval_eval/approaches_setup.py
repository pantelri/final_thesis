"""Constants and helpers for eval_approaches.py (moved verbatim from there)."""
from __future__ import annotations

import csv
import json
import logging
import os
from functools import partial
from pathlib import Path

from eval_retrieval import chunk_hit_at_k, max_recall_at_k, union_coverage_at_k

_ROOT = Path(__file__).resolve().parent.parent   # repository root (as in eval_approaches.py)
logger = logging.getLogger(__name__)

N_SAMPLES = 20
SEED      = 42
TOP_N     = 5


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_requirements_baseline() -> dict[str, dict]:
    req_file = _ROOT / "Requirements" / "offenlegungspflichten_gefiltert.json"
    data = json.loads(req_file.read_text(encoding="utf-8"))
    reqs = data.get("requirements", data) if isinstance(data, dict) else data
    return {r["id"]: r for r in reqs}


def load_requirements_enriched() -> dict[str, dict]:
    req_file = _ROOT / "Requirements" / "offenlegungspflichten_enriched.json"
    if not req_file.exists():
        logger.warning(
            "offenlegungspflichten_enriched.json nicht gefunden. "
            "Bitte generate_enriched_requirements.py zuerst ausführen. "
            "Approach 1 fällt auf Baseline zurück."
        )
        return {}
    data = json.loads(req_file.read_text(encoding="utf-8"))
    reqs = data.get("requirements", data) if isinstance(data, dict) else data
    return {r["id"]: r for r in reqs}


def setup_pipeline():
    from Ingestion.embed_pipeline import (
        COLLECTION_NAME, MODELS, _make_client, embed_query, open_collection,
    )
    from Retrieval import RetrievalReviewModule

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY nicht gesetzt.")

    for model_key in ("qwen3", "gemini"):
        try:
            collection = open_collection(model_key, COLLECTION_NAME)
            logger.info("Collection '%s' (%d Chunks).", model_key, collection.count())
            break
        except Exception:
            logger.warning("Collection '%s' nicht gefunden.", model_key)
    else:
        raise SystemExit("Keine ChromaDB-Collection gefunden.")

    or_client = _make_client(api_key)
    embed_fn  = partial(embed_query, model_id=MODELS[model_key], client=or_client)
    return RetrievalReviewModule(collection=collection, embed_fn=embed_fn)


def _safe_retrieve(module, query: str, company: str, top_n: int) -> list[dict]:
    try:
        return module.retrieve_raw(query, filters={"company": company}, top_n=top_n)
    except Exception as exc:
        logger.error("Retrieve-Fehler für %s: %s", company, exc)
        return []


def _metrics(raw: list[dict], gt_text: str) -> dict[str, float | int]:
    if not raw:
        return {"Hit@1": 0, "Hit@3": 0, "Hit@5": 0, "mr5": 0.0, "uc5": 0.0}
    return {
        "Hit@1": int(chunk_hit_at_k(raw, gt_text, k=1)),
        "Hit@3": int(chunk_hit_at_k(raw, gt_text, k=3)),
        "Hit@5": int(chunk_hit_at_k(raw, gt_text, k=5)),
        "mr5":   max_recall_at_k(raw, gt_text, k=TOP_N),
        "uc5":   union_coverage_at_k(raw, gt_text, k=TOP_N),
    }


