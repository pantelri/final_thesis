"""Verify chunk integrity after LLM splitting and apply automatic fixes.

Two invariants are checked for every non-table chunk:
  (A) len(text) <= MAX_CHARS
  (B) text appears verbatim (whitespace-normalised) in the original MD

Fix strategy:
  - LLM chunk fails (B) → re-extract from original offsets and rechunk
  - Any chunk fails (A) → rechunk_text fallback (hard word-boundary cut)
  - Table chunks are size-exempt but still checked for offset consistency
"""
from __future__ import annotations
import logging

from Ingestion.chunk_text import rechunk_text, MAX_CHARS

logger = logging.getLogger(__name__)


def _in_original(text: str, md_text: str) -> bool:
    """Whitespace-normalised substring check."""
    return ' '.join(text.split()) in ' '.join(md_text.split())


def verify_and_fix(
    chunks:  list[dict],
    md_text: str,
    company: str,
) -> tuple[list[dict], list[str]]:
    """
    Check every chunk for size and verbatim constraints; fix violations.

    Returns
    -------
    verified : list[dict]   – validated (and potentially replaced) chunks
    warnings : list[str]    – human-readable description of each fix applied
    """
    verified: list[dict] = []
    warnings: list[str]  = []

    for chunk in chunks:
        text = chunk['text']

        # ── Tables: size-exempt, only verify offset consistency ──────────────
        if chunk.get('is_table'):
            expected = md_text[chunk['char_start']:chunk['char_end']]
            if expected != text:
                w = (f"[{company}] Table offset mismatch "
                     f"@{chunk['char_start']}:{chunk['char_end']}")
                logger.warning(w)
                warnings.append(w)
                chunk = {**chunk, 'text': expected}  # repair text from offsets
            verified.append(chunk)
            continue

        # ── Text chunks ───────────────────────────────────────────────────────
        too_long    = len(text) > MAX_CHARS
        not_verbatim = not _in_original(text, md_text)

        if not too_long and not not_verbatim:
            verified.append(chunk)
            continue

        if not_verbatim and chunk.get('_llm_produced'):
            # LLM modified content → re-split from original offsets
            original_text = md_text[chunk['char_start']:chunk['char_end']]
            w = (f"[{company}] LLM chunk not verbatim "
                 f"@{chunk['char_start']}:{chunk['char_end']} – rechunking from source")
            logger.warning(w)
            warnings.append(w)
            fallback = rechunk_text({
                'heading_path': chunk['heading_path'],
                'char_start':   chunk['char_start'],
                'char_end':     chunk['char_end'],
                'text':         original_text,
            })
            verified.extend(fallback)
        elif too_long:
            w = (f"[{company}] Chunk still >{MAX_CHARS} chars ({len(text)}) "
                 f"@{chunk['char_start']}:{chunk['char_end']} – rechunking")
            logger.warning(w)
            warnings.append(w)
            verified.extend(rechunk_text(chunk))
        else:
            verified.append(chunk)

    return verified, warnings
