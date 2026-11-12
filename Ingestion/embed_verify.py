"""Quality verification of the embedded ChromaDB collections
(moved verbatim from Ingestion/embed_pipeline.py).

Usage:
    python -m Ingestion.embed_pipeline --verify
"""
from __future__ import annotations

import logging
import os
import random

import chromadb
import numpy as np
from openai import OpenAI

from Ingestion.embed_pipeline import MODELS, _make_client, embed_query, open_collection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quality verification
# ---------------------------------------------------------------------------

_TEST_QUERIES = [
    "Wie werden Rückstellungen im Jahresabschluss gebildet und bewertet?",
    "Was ist der Jahresfehlbetrag und wie beeinflusst er das Eigenkapital?",
    "Welche Bewertungsgrundsätze gelten für das Anlagevermögen nach HGB?",
    "Wie wird der Gewinnvortrag aus dem Vorjahr behandelt?",
    "Welche Angaben sind im Anhang zum Jahresabschluss Pflicht?",
]


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def test_heading_cohesion(
    collection: chromadb.Collection,
    n_pairs:    int = 300,
    seed:       int = 42,
) -> tuple[float, float]:
    """
    Measure whether heading-enrichment pulls same-heading chunks together.

    Samples n_pairs random chunk pairs and splits them into:
      intra: both chunks share the same (non-empty) heading_path
      inter: chunks have different heading_paths

    Returns (mean_intra_sim, mean_inter_sim).
    Healthy result: mean_intra >> mean_inter.
    """
    result    = collection.get(include=["embeddings", "metadatas"])
    vecs      = np.array(result["embeddings"], dtype=np.float32)
    headings  = [m["heading_path"] for m in result["metadatas"]]
    n         = len(vecs)

    if n < 2:
        logger.warning("Zu wenige Chunks für Kohärenztest.")
        return 0.0, 0.0

    rng         = random.Random(seed)
    intra_sims: list[float] = []
    inter_sims: list[float] = []

    # Targeted intra sampling: find headings with ≥2 chunks
    from collections import defaultdict
    heading_indices: dict[str, list[int]] = defaultdict(list)
    for idx, h in enumerate(headings):
        if h:
            heading_indices[h].append(idx)
    multi = [idxs for idxs in heading_indices.values() if len(idxs) >= 2]

    for _ in range(n_pairs // 2):
        if multi:
            idxs = rng.choice(multi)
            i, j = rng.sample(idxs, 2)
            intra_sims.append(_cosine_sim(vecs[i], vecs[j]))

    # Inter sampling
    all_idx = list(range(n))
    for _ in range(n_pairs // 2):
        i, j = rng.sample(all_idx, 2)
        if headings[i] != headings[j]:
            inter_sims.append(_cosine_sim(vecs[i], vecs[j]))

    mean_intra = sum(intra_sims) / len(intra_sims) if intra_sims else 0.0
    mean_inter = sum(inter_sims) / len(inter_sims) if inter_sims else 0.0
    return mean_intra, mean_inter


def test_retrieval(
    collection: chromadb.Collection,
    model_id:   str,
    client:     OpenAI,
    queries:    list[str] = _TEST_QUERIES,
    n_results:  int       = 3,
) -> None:
    """Embed test queries and print top-n retrieved chunks for manual inspection."""
    SEP = "─" * 70
    print(f"\n{'═' * 70}")
    print(f"  RETRIEVAL-TEST  |  Collection: {collection.name}")
    print(f"{'═' * 70}")

    for query in queries:
        q_vec = embed_query(query, model_id, client)
        res   = collection.query(
            query_embeddings=[q_vec],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        print(f"\n  Anfrage: \"{query}\"")
        print(SEP)
        for rank, (doc, meta, dist) in enumerate(
            zip(res["documents"][0], res["metadatas"][0], res["distances"][0]),
            start=1,
        ):
            sim     = 1.0 - dist
            heading = meta.get("heading_path", "–")[:65]
            company = meta.get("company", "?")
            preview = doc[:220].replace("\n", " ")
            print(f"  [{rank}] sim={sim:.4f}  {company}  |  {heading}")
            print(f"      {preview} …")
        print(SEP)


def verify(
    model_keys: list[str] | None = None,
    api_key:    str | None       = None,
) -> None:
    """Run heading-cohesion and retrieval tests for each available collection."""
    api_key    = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    model_keys = model_keys or list(MODELS.keys())

    for key in model_keys:
        model_id = MODELS[key]
        try:
            col = open_collection(key)
        except Exception:
            logger.warning("Collection für '%s' nicht gefunden – zuerst embed_pipeline ausführen.", key)
            continue

        client = _make_client(api_key)

        print(f"\n{'▓' * 70}")
        print(f"  MODELL: {key.upper()}  ({model_id})")
        print(f"  Chunks in Collection: {col.count()}")
        print(f"{'▓' * 70}")

        # Test 1: Heading cohesion
        intra, inter = test_heading_cohesion(col)
        delta = intra - inter
        status = "✓  gut" if delta > 0.03 else ("△  schwach" if delta > 0 else "✗  kein Effekt")
        print(f"\n  Heading-Kohärenz:")
        print(f"    Intra-Heading  (gleiche Überschrift): {intra:.4f}")
        print(f"    Inter-Heading  (versch. Überschrift): {inter:.4f}")
        print(f"    Δ = {delta:+.4f}  →  {status}")

        # Test 2: Retrieval
        test_retrieval(col, model_id, client)


