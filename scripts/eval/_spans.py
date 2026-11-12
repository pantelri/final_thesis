"""Robust span locator: map a GT element's (syntok-normalized) text back to char
offsets in the original .md document.

Why: passage_sentences.char_start/end are NULL, and the stored text is
syntok-joined (spaces inserted around punctuation; newlines collapsed; hyphenated
compounds re-spaced; '[...]' separators inserted), so it is not a byte-exact
substring of the md. We therefore match on the ALPHANUMERIC-ONLY projection of
both strings (drops whitespace, punctuation, and hyphens) and map the match back
to original md offsets. Case is preserved.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _strip_map(s: str) -> tuple[str, list[int]]:
    """Return (alphanumeric-only string, index map: stripped_pos -> original_pos)."""
    out_chars: list[str] = []
    idx_map: list[int] = []
    for i, ch in enumerate(s):
        if ch.isalnum():
            out_chars.append(ch)
            idx_map.append(i)
    return "".join(out_chars), idx_map


@lru_cache(maxsize=64)
def _md_index(md_path: str) -> tuple[str, str, tuple[int, ...]]:
    raw = Path(md_path).read_text(encoding="utf-8")
    stripped, idx_map = _strip_map(raw)
    return raw, stripped, tuple(idx_map)


def locate(md_path: str, element_text: str, hint_start: int | None = None) -> dict:
    """Find element_text in the md. Returns dict with char_start/char_end/status.

    status: 'exact' (located), 'multi' (located, multiple matches -> nearest hint),
            'notfound'. char_start/char_end are original-md offsets (end exclusive).
    """
    raw, md_stripped, idx_map = _md_index(md_path)
    needle, _ = _strip_map(element_text)
    if not needle:
        return {"char_start": None, "char_end": None, "status": "empty", "n_matches": 0}

    matches = []
    start = 0
    while True:
        pos = md_stripped.find(needle, start)
        if pos == -1:
            break
        matches.append(pos)
        start = pos + 1
    if not matches:
        return {"char_start": None, "char_end": None, "status": "notfound", "n_matches": 0}

    if len(matches) == 1 or hint_start is None:
        chosen = matches[0]
        status = "exact" if len(matches) == 1 else "multi"
    else:
        # pick the match whose original start offset is closest to the hint
        chosen = min(matches, key=lambda p: abs(idx_map[p] - hint_start))
        status = "multi"

    o_start = idx_map[chosen]
    o_end = idx_map[chosen + len(needle) - 1] + 1
    return {"char_start": o_start, "char_end": o_end, "status": status, "n_matches": len(matches)}
