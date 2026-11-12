"""Span- and chunk-level retrieval metrics (moved verbatim from eval_retrieval.py)."""
from __future__ import annotations

import re
from collections import Counter

# ── Deutsche Stoppwörter ──────────────────────────────────────────────────────

_STOPWORDS = {
    "der", "die", "das", "dem", "den", "des",
    "ein", "eine", "einen", "einem", "einer", "eines",
    "ich", "du", "er", "sie", "es", "wir", "ihr",
    "mich", "dich", "ihn", "uns", "euch", "ihm", "ihnen", "sich", "man",
    "in", "an", "auf", "für", "von", "zu", "mit", "als",
    "bei", "nach", "vor", "durch", "über", "unter", "um",
    "zwischen", "gegen", "aus", "seit", "bis", "ohne",
    "während", "wegen", "trotz", "statt", "ab", "entgegen",
    "und", "oder", "aber", "denn", "weil", "dass", "wenn",
    "ob", "auch", "noch", "schon", "bereits", "nur", "nicht",
    "kein", "keine", "jedoch", "daher", "damit", "dabei",
    "dazu", "davon", "daran", "darauf", "darin", "darüber",
    "darunter", "dort", "hier", "so", "wie", "was", "wer",
    "wen", "wem", "nun", "dann", "zwar", "darum",
    "deshalb", "sondern", "sowie", "bzw", "d.h", "ggf",
    "z.b", "u.a", "ca", "inkl", "exkl", "vgl", "gem",
    "ist", "sind", "war", "waren", "wird", "werden", "wurde",
    "wurden", "hat", "haben", "hatte", "hatten", "kann",
    "können", "muss", "müssen", "soll", "sollen", "darf",
    "dürfen", "worden", "sein",
}


def _normalize_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\b\w+\b", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _token_f1(pred_text: str, ref_text: str) -> tuple[float, float, float]:
    pred_tok = Counter(_normalize_tokens(pred_text))
    ref_tok  = Counter(_normalize_tokens(ref_text))
    if not ref_tok or not pred_tok:
        return 0.0, 0.0, 0.0
    common    = sum((pred_tok & ref_tok).values())
    recall    = common / sum(ref_tok.values())
    precision = common / sum(pred_tok.values())
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return round(recall, 4), round(precision, 4), round(f1, 4)


def squad_f1(pred_text: str, gt_text: str) -> tuple[float, float, float]:
    """SQuAD-F1 über den gesamten GT — [...]-Trenner werden vor Tokenisierung entfernt."""
    return _token_f1(pred_text, gt_text.replace("[...]", " "))


def max_subspan_f1(pred_text: str, gt_text: str) -> float:
    """Max-F1 über einzelne GT-Subspans — entkoppelt den Längen-Bias des Agenten."""
    subspans = [s.strip() for s in gt_text.split("[...]") if s.strip()]
    if not subspans:
        return squad_f1(pred_text, gt_text)[2]
    return max(_token_f1(pred_text, sub)[2] for sub in subspans)


# ── Chunk-Level-Metriken ──────────────────────────────────────────────────────

def _subspan_recall_in_chunk(chunk_text: str, subspan_text: str) -> float:
    """Token-Recall des Subspans relativ zum Chunk (wie viel GT-Inhalt ist im Chunk)."""
    chunk_tok   = Counter(_normalize_tokens(chunk_text))
    subspan_tok = Counter(_normalize_tokens(subspan_text))
    if not subspan_tok:
        return 0.0
    common = sum((chunk_tok & subspan_tok).values())
    return common / sum(subspan_tok.values())


def subspan_overlaps(raw_candidates: list[dict], gt_text: str) -> list[dict]:
    """Pro GT-Subspan: maximaler Token-Recall über alle Top-k-Chunks (float 0–1).

    Gibt eine Liste mit einem Eintrag pro Subspan zurück:
        subspan_idx, subspan_text (gekürzt), max_recall, best_rank, best_chunk_id
    """
    subspans = [s.strip() for s in gt_text.split("[...]") if s.strip()] or [gt_text.strip()]
    results  = []
    for idx, sub in enumerate(subspans):
        best_recall = 0.0
        best_rank   = -1
        best_id     = ""
        for cand in raw_candidates:
            r = _subspan_recall_in_chunk(cand.get("text", ""), sub)
            if r > best_recall:
                best_recall = r
                best_rank   = cand["rank"]
                best_id     = cand["chunk_id"]
        results.append({
            "subspan_idx":       idx,
            "subspan_text":      sub[:120] + ("…" if len(sub) > 120 else ""),
            "max_recall_top_k":  round(best_recall, 4),
            "best_rank":         best_rank,
            "best_chunk_id":     best_id,
        })
    return results


def chunk_hit_at_k(raw_candidates: list[dict], gt_text: str,
                   k: int, threshold: float = 0.5) -> bool:
    """(a) Boolean: hat ein einzelner Top-k-Chunk Recall ≥ threshold für irgendeinen Subspan?"""
    subspans = [s.strip() for s in gt_text.split("[...]") if s.strip()] or [gt_text.strip()]
    for cand in raw_candidates[:k]:
        for sub in subspans:
            if _subspan_recall_in_chunk(cand.get("text", ""), sub) >= threshold:
                return True
    return False


def max_recall_at_k(raw_candidates: list[dict], gt_text: str, k: int) -> float:
    """(a) Kontinuierlich: max Token-Recall eines einzelnen Chunks über alle Subspans."""
    subspans = [s.strip() for s in gt_text.split("[...]") if s.strip()] or [gt_text.strip()]
    best = 0.0
    for cand in raw_candidates[:k]:
        for sub in subspans:
            r = _subspan_recall_in_chunk(cand.get("text", ""), sub)
            if r > best:
                best = r
    return round(best, 4)


def union_coverage_at_k(raw_candidates: list[dict], gt_text: str, k: int) -> float:
    """(b) Union-Coverage: decken Top-k Chunks gemeinsam den GT-Subspan ab?

    Coverage = |∪(chunk_token_typen[:k]) ∩ subspan_token_typen| / |subspan_token_typen|
    Richtung: Chunk→Subspan (wie viel des GT ist erreichbar).
    Verwendet Typ-Sets (kein Counting), robust gegen Chunk-Größenvarianz.
    """
    subspans = [s.strip() for s in gt_text.split("[...]") if s.strip()] or [gt_text.strip()]
    best = 0.0
    for sub in subspans:
        sub_types = set(_normalize_tokens(sub))
        if not sub_types:
            continue
        union_types: set[str] = set()
        for cand in raw_candidates[:k]:
            union_types.update(_normalize_tokens(cand.get("text", "")))
        cov = len(sub_types & union_types) / len(sub_types)
        if cov > best:
            best = cov
    return round(best, 4)

