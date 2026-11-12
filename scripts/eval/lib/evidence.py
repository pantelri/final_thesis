"""Evidence passages for Stage-3 fulfillment verification.

Two retrieval conditions:
  predicted(company, obl, k) : top-k passages from the Phase-3 retrieval WINNER
      (gemini / baseSeg / llmdesc / enriched). The enriched query for each of the
      13 obligations was already embedded in Phase 3, so this is cache-free of new
      embedding calls in practice.
  oracle(company, obl)       : the curated GT evidence spans for the pair, taken
      from retrieval_gt_snapshot.csv WITHOUT the is_relevant filter (so the 8
      applicable-but-is_relevant=f pairs still get their post-rebuild evidence).
      This deliberately does NOT touch lib.gt.gt_positives() (is_relevant=t), which
      remains the retrieval-GT definition for Phase 3.

Passage text is sliced verbatim from the company .md by char offsets, so it is
identical to the corpus chunk / GT text.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

import pandas as pd

from scripts.eval._common import MD_DIR
from scripts.eval.lib.chroma import retrieve
from scripts.eval.lib.embedder import QueryEmbedder
from scripts.eval.lib.gt import GT_SNAPSHOT
from scripts.eval.lib.queries import query_enriched

# Phase-3 retrieval winner (see results/retrieval_winner.csv).
WINNER_COLLECTION = "google001_baseSeg_llmdesc"
WINNER_EMBED = "gemini"
DEFAULT_K = 5


@lru_cache(maxsize=32)
def _md(company: str) -> str:
    return (MD_DIR / f"{company}.md").read_text(encoding="utf-8")


def _slice(company: str, start: int, end: int) -> str:
    return _md(company)[start:end]


@lru_cache(maxsize=1)
def _embedder() -> QueryEmbedder:
    return QueryEmbedder(WINNER_EMBED)


def _reorder(passages: list[tuple[int, int, str]], order: str) -> list[tuple[int, int, str]]:
    """Reorder retrieval hits (RQ5 passage-position study).

    rank           : as retrieved — most-relevant FIRST (default, current behaviour).
    doc            : source-document order — sort by char_start ascending.
    relevance_last : most-relevant LAST — exploits the U-shaped attention span when
                     the instruction sits at the top of the prompt.
    """
    if order == "rank":
        return passages
    if order == "doc":
        return sorted(passages, key=lambda p: p[0])
    if order == "relevance_last":
        return list(reversed(passages))
    raise ValueError(f"unknown passage order {order!r}")


def predicted_passages(company: str, obl: str, k: int = DEFAULT_K,
                       order: str = "rank") -> list[tuple[int, int, str]]:
    """Top-k retrieval-winner passages for the pair, as (char_start, char_end, text)."""
    vec = _embedder().embed(query_enriched(obl))
    spans = retrieve(WINNER_COLLECTION, vec, company, k)
    passages = [(s, e, _slice(company, s, e)) for (s, e) in spans]
    return _reorder(passages, order)


@lru_cache(maxsize=1)
def _oracle_spans() -> dict[tuple[str, str], list[tuple[int, int]]]:
    """(company, obligation) -> sorted unique GT evidence spans (NO is_relevant filter)."""
    df = pd.read_csv(GT_SNAPSHOT, dtype=str, keep_default_na=False)
    df = df[(df["char_start"] != "") & (df["char_end"] != "")]
    out: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    for r in df.itertuples(index=False):
        out[(r.company_id, r.obligation_id)].add((int(float(r.char_start)), int(float(r.char_end))))
    return {k: sorted(v) for k, v in out.items()}


def oracle_passages(company: str, obl: str) -> list[tuple[int, int, str]]:
    """Curated GT evidence passages for the pair, as (char_start, char_end, text)."""
    spans = _oracle_spans().get((company, obl), [])
    return [(s, e, _slice(company, s, e)) for (s, e) in spans]


def evidence(company: str, obl: str, condition: str, k: int = DEFAULT_K,
             order: str = "rank") -> list[tuple[int, int, str]]:
    if condition == "predicted":
        return predicted_passages(company, obl, k, order)
    if condition == "oracle":
        return oracle_passages(company, obl)
    raise ValueError(f"unknown retrieval condition {condition!r}")
