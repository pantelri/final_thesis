"""Span-overlap retrieval metrics: recall / hit / precision / reciprocal-rank for
the top-k retrieved chunk spans against the GT evidence spans (md char offsets)."""
from __future__ import annotations


def overlaps(chunk: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    cs, ce = chunk
    return any(cs < e and s < ce for s, e in spans)


def metrics_at_k(retrieved: list[tuple[int, int]], spans: list[tuple[int, int]], k: int) -> dict:
    """recall/hit/precision/rr for the top-k retrieved chunks vs GT spans.

    recall    : fraction of GT spans overlapped by >=1 retrieved chunk (coverage).
    hit       : 1.0 if any retrieved chunk overlaps a GT span.
    precision : fraction of the top-k chunks that overlap a GT span.
    rr        : reciprocal rank of the first overlapping chunk.
    """
    topk = retrieved[:k]
    hits = [overlaps(c, spans) for c in topk]
    n_rel_chunks = sum(hits)
    covered = sum(1 for s in spans if any(overlaps(c, [s]) for c in topk))
    recall = covered / len(spans) if spans else 0.0
    precision = n_rel_chunks / k if k else 0.0
    hit = 1.0 if n_rel_chunks > 0 else 0.0
    rr = 0.0
    for rank, h in enumerate(hits, 1):
        if h:
            rr = 1.0 / rank
            break
    return {"recall": recall, "hit": hit, "precision": precision, "rr": rr}
