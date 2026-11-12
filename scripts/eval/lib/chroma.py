"""ChromaDB access for retrieval: open a collection and fetch the top-k chunk
spans for a target company (retrieval is restricted to the company's report)."""
from __future__ import annotations

from functools import lru_cache

import chromadb

from scripts.eval._common import COLLECTIONS


@lru_cache(maxsize=16)
def open_collection(collection_key: str):
    spec = COLLECTIONS[collection_key]
    db = chromadb.PersistentClient(path=str(spec.chroma_dir))
    return db.get_collection(name=spec.name)


def retrieve(collection_key: str, query_vec: list[float], company: str, top_k: int = 7):
    """Return [(chunk_char_start, chunk_char_end), ...] for the top_k chunks of the
    given company."""
    col = open_collection(collection_key)
    res = col.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where={"company": company},
        include=["metadatas"],
    )
    metas = res["metadatas"][0] if res["metadatas"] else []
    return [(int(m["char_start"]), int(m["char_end"])) for m in metas]
