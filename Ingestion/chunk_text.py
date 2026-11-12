"""Rechunk text pieces to ≤MAX_CHARS characters with ~OVERLAP_PCT overlap.

Chunks are sliced from the original text at word boundaries so their text is
always a verbatim substring of the source document.
"""
from __future__ import annotations

MAX_CHARS   = 701
OVERLAP_PCT = 0.12          # 12 % ⟹ ~84-char overlap between adjacent chunks
_OVERLAP    = int(MAX_CHARS * OVERLAP_PCT)   # 84


def _split_positions(text: str, max_chars: int, overlap: int) -> list[tuple[int, int]]:
    """
    Return (start, end) character positions within *text* for each chunk.
    End is snapped to the last space within the window to avoid mid-word cuts.
    Hard-cuts only if no space is found (e.g. a very long token).
    """
    if len(text) <= max_chars:
        return [(0, len(text))]

    step      = max_chars - overlap
    positions = []
    start     = 0

    while start < len(text):
        end = min(start + max_chars, len(text))

        # Snap end backward to a word boundary
        if end < len(text):
            snap = text.rfind(' ', start, end)
            if snap > start:
                end = snap + 1          # include the trailing space

        positions.append((start, end))

        if end >= len(text):
            break

        # Advance by step, then snap forward to the start of a word
        next_start = start + step
        if next_start < end:
            # Advance past any partial word
            while next_start < end and not text[next_start].isspace():
                next_start += 1
            # Skip whitespace
            while next_start < end and text[next_start].isspace():
                next_start += 1
        start = next_start if next_start < len(text) else len(text)

    return positions


def rechunk_text(piece: dict, max_chars: int = MAX_CHARS) -> list[dict]:
    """
    Split a text piece (with char_start, char_end, text) into chunks of
    ≤max_chars characters. Returns a list of chunk dicts with updated offsets.
    """
    text      = piece['text']
    abs_start = piece['char_start']

    if not text.strip():
        return []

    positions = _split_positions(text, max_chars, _OVERLAP)

    return [
        {
            'heading_path': piece['heading_path'],
            'char_start':   abs_start + s,
            'char_end':     abs_start + e,
            'text':         text[s:e],
            'is_table':     False,
        }
        for s, e in positions
        if text[s:e].strip()
    ]
