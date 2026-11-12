"""Phase 2 — embed corpus collections into ChromaDB.

Two table representations (table_rep factor):
  raw_md  : embed the verbatim markdown table (heading + md). Original behaviour;
            the 4 raw_md collections already exist.
  llmdesc : embed a Qwen3.7-Max plain-text description of each table instead of its
            markdown. NON-table chunks are identical to raw_md, so their vectors are
            COPIED from the raw_md sibling collection (saves cost and isolates the
            table_rep factor — the only difference between the two arms is the table
            embedding). Only the 127 table descriptions are embedded via the API,
            cached by (embed_model, input-hash) so the two segmentations share work.

The stored ChromaDB document + offsets remain the verbatim md in both arms, so GT
span overlap and verification are unaffected.

Run: python -m scripts.eval.phase2_embed [--model gemini|qwen3] [--table-rep raw_md|llmdesc]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time

from Ingestion.embed_pipeline import build_embed_text, load_chunks, upsert_collection

from scripts.eval._common import (
    CHUNKS_BY_SEG, COLLECTIONS, EMBED_MODELS, RESULTS, TABLE_SUMMARIES_JSONL,
    load_openrouter_key,
)
from scripts.eval.lib.chroma import open_collection
from scripts.eval.lib.embedder import truncate_tokens
from scripts.eval.lib.openrouter import make_client

BATCH_SIZE = 32
MAX_RETRIES = 12                      # OpenRouter gemini endpoint is flaky (empty payloads)
GEMINI_DOC_MAX_TOKENS = 1800          # same safe budget as queries (2048 model limit)
_EMB_CACHE_DIR = RESULTS / "_qcache"


# --------------------------------------------------------------------------- #
# Resilient batch embedding (retry/backoff; split on persistent failure)
# --------------------------------------------------------------------------- #
def _embed_batch(batch, model_id, client, bi, total):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.embeddings.create(model=model_id, input=batch)
            if not resp.data:
                raise ValueError("empty embedding payload")
            ordered = sorted(resp.data, key=lambda x: x.index)
            print(f"  batch {bi}/{total} ({len(batch)}) ok")
            return [item.embedding for item in ordered]
        except Exception as exc:
            wait = min(2 ** attempt, 30) + random.uniform(0, 3)   # jitter de-correlates retries
            print(f"  batch {bi}/{total} attempt {attempt} failed: {str(exc)[:80]} -> retry in {wait:.1f}s")
            time.sleep(wait)
    if len(batch) > 1:
        print(f"  batch {bi}/{total}: splitting after {MAX_RETRIES} failures")
        mid = len(batch) // 2
        return (_embed_batch(batch[:mid], model_id, client, bi, total)
                + _embed_batch(batch[mid:], model_id, client, bi, total))
    raise RuntimeError(f"batch {bi}/{total} permanently failed: {batch[0][:60]!r}")


def embed_texts_resilient(texts, model_id, client):
    vectors = []
    total = math.ceil(len(texts) / BATCH_SIZE) or 1
    for bi, start in enumerate(range(0, len(texts), BATCH_SIZE), 1):
        vectors.extend(_embed_batch(texts[start:start + BATCH_SIZE], model_id, client, bi, total))
        if bi < total:
            time.sleep(0.3)
    return vectors


# --------------------------------------------------------------------------- #
# llmdesc helpers
# --------------------------------------------------------------------------- #
def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_summaries() -> dict[str, str]:
    """table text-hash -> Qwen3.7-Max description."""
    out = {}
    for line in TABLE_SUMMARIES_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["text_hash"]] = rec["summary"]
    return out


def _llmdesc_input(chunk: dict, summaries: dict[str, str], embed_key: str) -> str:
    """Embedding input for the llmdesc arm: heading + (summary if table else text)."""
    if chunk.get("is_table"):
        summary = summaries.get(_sha1(chunk["text"]))
        if not summary:                       # safety net: fall back to raw md
            summary = chunk["text"]
        heading = (chunk.get("heading_path") or "").strip()
        text = f"{heading}\n\n{summary}" if heading else summary
    else:
        text = build_embed_text(chunk)
    if embed_key == "gemini":
        text = truncate_tokens(text, GEMINI_DOC_MAX_TOKENS)
    return text


def _raw_md_sibling(embed_key: str, seg: str) -> str:
    for key, spec in COLLECTIONS.items():
        if spec.embed == embed_key and spec.seg == seg and spec.table_rep == "raw_md":
            return key
    raise KeyError(f"no raw_md sibling for {embed_key}/{seg}")


def _table_vec_cache(embed_key: str) -> tuple[dict, "object"]:
    """Disk cache of table-description vectors keyed by input-hash (per model)."""
    path = _EMB_CACHE_DIR / f"tabemb_{embed_key}.jsonl"
    cache = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                cache[rec["h"]] = rec["v"]
    return cache, path


# --------------------------------------------------------------------------- #
# Collection builders
# --------------------------------------------------------------------------- #
def embed_raw_md(collection_key, api_key):
    spec = COLLECTIONS[collection_key]
    chunks = load_chunks(CHUNKS_BY_SEG[spec.seg])
    client = make_client(api_key)
    print(f"=== {collection_key}  raw_md  ({EMBED_MODELS[spec.embed]}) -> {spec.chroma_dir}")
    vectors = embed_texts_resilient([build_embed_text(c) for c in chunks], EMBED_MODELS[spec.embed], client)
    col = upsert_collection(chunks, vectors, spec.chroma_dir, collection_name=spec.name)
    print(f"    upserted {col.count()} chunks")


def embed_llmdesc(collection_key, api_key, summaries):
    spec = COLLECTIONS[collection_key]
    model_id = EMBED_MODELS[spec.embed]
    chunks = load_chunks(CHUNKS_BY_SEG[spec.seg])
    print(f"=== {collection_key}  llmdesc  ({model_id}) -> {spec.chroma_dir}")

    # 1) reuse non-table vectors from the raw_md sibling
    sibling = _raw_md_sibling(spec.embed, spec.seg)
    src = open_collection(sibling)
    ids = [c["chunk_id"] for c in chunks]
    got = src.get(ids=ids, include=["embeddings"])
    src_vec = {cid: (vec.tolist() if hasattr(vec, "tolist") else list(vec))
               for cid, vec in zip(got["ids"], got["embeddings"])}

    # 2) embed table descriptions (cached by input-hash), reuse text vectors
    cache, cache_path = _table_vec_cache(spec.embed)
    client = None
    n_table, n_reused, n_new, n_miss = 0, 0, 0, 0
    vectors = []
    for c in chunks:
        if c.get("is_table"):
            n_table += 1
            inp = _llmdesc_input(c, summaries, spec.embed)
            h = _sha1(inp)
            if h in cache:
                vectors.append(cache[h])
            else:
                if client is None:
                    client = make_client(api_key)
                vec = embed_texts_resilient([inp], model_id, client)[0]
                cache[h] = vec
                with open(cache_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"h": h, "v": vec}) + "\n")
                n_new += 1
                vectors.append(vec)
        else:
            vec = src_vec.get(c["chunk_id"])
            if vec is None:                    # fallback: chunk missing in sibling
                if client is None:
                    client = make_client(api_key)
                vec = embed_texts_resilient([build_embed_text(c)], model_id, client)[0]
                n_miss += 1
            else:
                n_reused += 1
            vectors.append(vec)

    col = upsert_collection(chunks, vectors, spec.chroma_dir, collection_name=spec.name)
    print(f"    tables={n_table} (new-embedded {n_new}, cached {n_table - n_new}); "
          f"text reused={n_reused}, text re-embedded(miss)={n_miss}")
    print(f"    upserted {col.count()} chunks")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["gemini", "qwen3"], help="only this embedding model")
    ap.add_argument("--table-rep", choices=["raw_md", "llmdesc"], default="llmdesc",
                    help="which arm to build (default: llmdesc — the new collections)")
    args = ap.parse_args()

    api_key = load_openrouter_key()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not found (env or annotation_app/.env)")

    targets = [k for k, v in COLLECTIONS.items()
               if v.table_rep == args.table_rep and (args.model is None or v.embed == args.model)]
    print(f"table_rep={args.table_rep}  targets={targets}")

    summaries = load_summaries() if args.table_rep == "llmdesc" else {}
    if args.table_rep == "llmdesc":
        print(f"loaded {len(summaries)} table summaries")

    for k in targets:
        if args.table_rep == "llmdesc":
            embed_llmdesc(k, api_key, summaries)
        else:
            embed_raw_md(k, api_key)


if __name__ == "__main__":
    main()
