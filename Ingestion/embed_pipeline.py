"""Embed HGB-Chunks in ChromaDB via OpenRouter.

Two ChromaDB collections are built, one per model:
  qwen/qwen3-embedding-8b      → Output/chromadb/qwen3/
  google/gemini-embedding-001  → Output/chromadb/gemini/

Heading enrichment: every chunk is embedded as
    <heading_path>

    <text>
so that chunks under the same heading cluster in vector space.
The stored ChromaDB document contains only the original text (not enriched),
so retrieval returns clean, readable passages.

Queries must be embedded WITHOUT the heading prefix (asymmetric setup).
Use embed_query() or pass query_embeddings= to collection.query().

Usage:
    python -m Ingestion.embed_pipeline              # both models
    python -m Ingestion.embed_pipeline --model qwen3    # Qwen3 only
    python -m Ingestion.embed_pipeline --model gemini   # Gemini only
    python -m Ingestion.embed_pipeline --verify     # quality checks only

Required:
    OPENROUTER_API_KEY environment variable
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import time
from pathlib import Path

import chromadb
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

_ROOT       = Path(__file__).parent.parent
JSONL_PATH  = _ROOT / "Output" / "chunks" / "chunks.jsonl"
CHROMA_BASE = _ROOT / "Output" / "chromadb"

MODELS: dict[str, str] = {
    "qwen3":  "qwen/qwen3-embedding-8b",
    "gemini": "google/gemini-embedding-001",
}

COLLECTION_NAME = "hgb_chunks"
BATCH_SIZE      = 32
BATCH_SLEEP     = 0.3   # seconds between batches to stay within rate limits


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_chunks(path: Path = JSONL_PATH) -> list[dict]:
    chunks: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    logger.info("Geladen: %d Chunks aus %s", len(chunks), path)
    return chunks


# ---------------------------------------------------------------------------
# Embedding text construction
# ---------------------------------------------------------------------------

def build_embed_text(chunk: dict) -> str:
    """Enriched text for *document* embedding: heading_path + text.

    Chunks with the same heading share a common prefix, which pulls their
    vectors closer together in the embedding space.
    """
    heading = (chunk.get("heading_path") or "").strip()
    text    = (chunk.get("text") or "").strip()
    return f"{heading}\n\n{text}" if heading else text


def build_query_text(query: str) -> str:
    """Plain query — no heading prefix (asymmetric retrieval)."""
    return query.strip()


# ---------------------------------------------------------------------------
# Embedding via OpenRouter
# ---------------------------------------------------------------------------

def _make_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def embed_texts(
    texts:      list[str],
    model_id:   str,
    client:     OpenAI,
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """Embed all texts in batches; return a list of embedding vectors."""
    all_vectors: list[list[float]] = []
    total = math.ceil(len(texts) / batch_size)

    for idx, start in enumerate(range(0, len(texts), batch_size), 1):
        batch = texts[start : start + batch_size]
        logger.info("  Batch %d/%d  (%d Texte) …", idx, total, len(batch))
        response = client.embeddings.create(model=model_id, input=batch)
        ordered  = sorted(response.data, key=lambda x: x.index)
        all_vectors.extend(item.embedding for item in ordered)
        if idx < total:
            time.sleep(BATCH_SLEEP)

    return all_vectors


def embed_query(
    query:    str,
    model_id: str,
    client:   OpenAI,
) -> list[float]:
    """Embed a single query (no heading prefix)."""
    response = client.embeddings.create(model=model_id, input=[build_query_text(query)])
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# ChromaDB storage
# ---------------------------------------------------------------------------

def upsert_collection(
    chunks:          list[dict],
    embeddings:      list[list[float]],
    chroma_dir:      Path,
    collection_name: str = COLLECTION_NAME,
) -> chromadb.Collection:
    """Upsert chunks with pre-computed embeddings into a ChromaDB collection."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    db = chromadb.PersistentClient(path=str(chroma_dir))

    # No embedding_function — all embeddings are pre-computed.
    # Queries must use query_embeddings=, not query_texts=.
    collection = db.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids       = [c["chunk_id"] for c in chunks]
    documents = [c["text"]     for c in chunks]
    metadatas = [
        {
            "company":      c["company"],
            "heading_path": c.get("heading_path") or "",
            "char_start":   c["char_start"],
            "char_end":     c["char_end"],
            "is_table":     int(bool(c.get("is_table", False))),
            "n_tokens":     c.get("n_tokens", 0),
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info(
        "ChromaDB '%s': %d Chunks → %s",
        collection_name, collection.count(), chroma_dir,
    )
    return collection


def open_collection(model_key: str, collection_name: str = COLLECTION_NAME) -> chromadb.Collection:
    """Open an existing ChromaDB collection (read-only access)."""
    chroma_dir = CHROMA_BASE / model_key
    db = chromadb.PersistentClient(path=str(chroma_dir))
    return db.get_collection(name=collection_name)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_model(
    model_key: str,
    chunks:    list[dict],
    api_key:   str,
) -> chromadb.Collection | None:
    model_id   = MODELS[model_key]
    chroma_dir = CHROMA_BASE / model_key
    client     = _make_client(api_key)

    logger.info("=== %s  (%s) ===", model_key.upper(), model_id)

    embed_inputs = [build_embed_text(c) for c in chunks]
    try:
        vectors = embed_texts(embed_inputs, model_id, client)
    except Exception as exc:
        logger.error("Embedding fehlgeschlagen für %s: %s", model_id, exc)
        return None

    return upsert_collection(chunks, vectors, chroma_dir)


def run(
    model_keys: list[str] | None = None,
    api_key:    str | None       = None,
    jsonl_path: Path             = JSONL_PATH,
) -> None:
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY nicht gesetzt.\n"
            "Bitte setzen: $env:OPENROUTER_API_KEY = 'sk-or-...'"
        )

    if model_keys is None:
        model_keys = list(MODELS.keys())

    unknown = [k for k in model_keys if k not in MODELS]
    if unknown:
        raise ValueError(f"Unbekannte Modelle: {unknown}. Verfügbar: {list(MODELS.keys())}")

    chunks = load_chunks(jsonl_path)
    for key in model_keys:
        run_model(key, chunks, api_key)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Embed HGB-Chunks via OpenRouter → ChromaDB"
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        help="Nur dieses Modell ausführen (default: beide)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Nur Qualitätsprüfung – kein Embedding",
    )
    args = parser.parse_args()

    model_keys = [args.model] if args.model else None

    if args.verify:
        from Ingestion.embed_verify import verify
        verify(model_keys=model_keys)
    else:
        run(model_keys=model_keys)
