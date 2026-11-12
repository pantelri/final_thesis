"""Offset spot check, oracle retrievability and agent delta
(moved verbatim from eval_retrieval.py)."""
from __future__ import annotations

import logging
import random

from retrieval_eval.metrics import _subspan_recall_in_chunk

logger = logging.getLogger(__name__)


# ── Offset-Spot-Check ─────────────────────────────────────────────────────────

def run_offset_spot_check(module, gt_spans_rows: list[dict], n: int = 3) -> list[dict]:
    """Für n GT-Subspans: finde den char-offset-überlappenden Chunk und prüfe Substring.

    Auswahl: die n GT-Spans mit dem höchsten char-Offset-Overlap mit irgendeinem Chunk.
    Ausgabe pro Fall:
        company, label, span_start, span_end, span_len,
        best_chunk_id, chunk_start, chunk_end, offset_overlap_chars, offset_overlap_ratio,
        substring_match (bool), token_recall
    """
    # Kurze Spans bevorzugen (≤ 701 Chars — passen potenziell in einen Chunk)
    short_spans = sorted(
        [r for r in gt_spans_rows if int(r["char_len"]) <= 701],
        key=lambda r: int(r["char_len"])
    )
    candidates = short_spans[:20]   # Pool der kürzesten für Auswahl
    rng        = random.Random(0)
    selected   = rng.sample(candidates, min(n, len(candidates)))

    results = []
    for span in selected:
        company    = span["company"]
        label      = span["label"]
        span_start = int(span["start"])
        span_end   = int(span["end"])
        span_text  = span["text"]

        # Alle Chunks der Firma laden
        try:
            all_chunks = module.get_all_chunks_for_company(company)
        except Exception as exc:
            logger.error("get_all_chunks_for_company Fehler: %s", exc)
            continue

        # Chunk mit maximalem Char-Offset-Overlap finden
        best = None
        best_overlap = -1
        for chunk in all_chunks:
            cs, ce = chunk["char_start"], chunk["char_end"]
            overlap = max(0, min(ce, span_end) - max(cs, span_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best         = chunk

        if best is None:
            continue

        span_len           = span_end - span_start
        overlap_ratio      = round(best_overlap / span_len, 4) if span_len > 0 else 0.0
        substring_match    = span_text.strip() in best["text"]
        tok_recall         = round(_subspan_recall_in_chunk(best["text"], span_text), 4)

        entry = {
            "company":               company,
            "label":                 label,
            "span_start":            span_start,
            "span_end":              span_end,
            "span_len":              span_len,
            "best_chunk_id":         best["chunk_id"],
            "chunk_start":           best["char_start"],
            "chunk_end":             best["char_end"],
            "offset_overlap_chars":  best_overlap,
            "offset_overlap_ratio":  overlap_ratio,
            "substring_match":       substring_match,
            "token_recall":          tok_recall,
        }
        results.append(entry)

        logger.info(
            "Spot-Check | %s %s | Overlap=%.0f/%d (%.1f%%) | Substring=%s | TokenRecall=%.3f",
            company, label, best_overlap, span_len, overlap_ratio * 100,
            substring_match, tok_recall,
        )

    return results


# ── Oracle-Retrievability-Check ──────────────────────────────────────────────

def oracle_rank_for_case(
    module,
    company: str,
    label: str,
    gt_spans_index: dict,
    top_n: int = 20,
) -> list[dict]:
    """Für jeden GT-Subspan: embedde Subspan-Text als Query, gib Rang des Oracle-Chunks zurück.

    Oracle-Chunk = Chunk mit maximalem Char-Offset-Overlap zum GT-Subspan (aus df1_spans).
    Gibt eine Liste mit einem Eintrag pro Subspan zurück:
        subspan_idx, oracle_chunk_id, oracle_rank (None wenn nicht in top_n), offset_overlap_ratio
    """
    spans = gt_spans_index.get((company, label), [])
    if not spans:
        return []

    try:
        all_chunks = module.get_all_chunks_for_company(company)
    except Exception as exc:
        logger.error("get_all_chunks_for_company Fehler: %s", exc)
        return []

    results = []
    for idx, span in enumerate(spans):
        span_start = int(span["start"])
        span_end   = int(span["end"])
        span_text  = span["text"]
        span_len   = span_end - span_start

        # Oracle-Chunk per Offset-Overlap bestimmen
        oracle_id    = None
        best_overlap = -1
        for chunk in all_chunks:
            cs, ce = chunk["char_start"], chunk["char_end"]
            ov = max(0, min(ce, span_end) - max(cs, span_start))
            if ov > best_overlap:
                best_overlap = ov
                oracle_id    = chunk["chunk_id"]

        if oracle_id is None:
            continue

        # Subspan-Text als Query embedden und retrieven
        try:
            oracle_raw = module.retrieve_raw(
                span_text, filters={"company": company}, top_n=top_n
            )
        except Exception as exc:
            logger.error("Oracle-Retrieve Fehler: %s", exc)
            oracle_raw = []

        oracle_rank = next(
            (c["rank"] for c in oracle_raw if c["chunk_id"] == oracle_id), None
        )

        entry = {
            "subspan_idx":          idx,
            "oracle_chunk_id":      oracle_id,
            "oracle_rank":          oracle_rank,
            "offset_overlap_ratio": round(best_overlap / span_len, 3) if span_len else 0.0,
        }
        results.append(entry)
        logger.info(
            "  Oracle | sub=%d | chunk=%s | rank=%s | overlap=%.1f%%",
            idx, oracle_id, oracle_rank, (best_overlap / span_len * 100) if span_len else 0,
        )

    return results


# ── Agent-Delta ───────────────────────────────────────────────────────────────

def agent_delta(raw_candidates: list[dict], result) -> dict:
    """Welche Chunk-IDs hat der Agent übernommen vs. welche lagen in den Top-5?

    Zeigt das Zollern-Muster: Chunk war da, Agent hat ihn nicht hinzugefügt.
    """
    top5_ids  = [c["chunk_id"] for c in raw_candidates]
    agent_ids = result.metadata.get("chunk_ids", []) if result else []
    return {
        "top5_ids":        top5_ids,
        "agent_ids":       agent_ids,
        "dropped_by_agent":  [cid for cid in top5_ids  if cid not in agent_ids],
        "added_by_expand":   [cid for cid in agent_ids  if cid not in top5_ids],
    }


