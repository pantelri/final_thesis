"""Split a .md document into verbatim units used for fuzzy matching."""
from .normalize import norm_map


def md_candidates(text: str):
    """Verbatim .md units for fuzzy matching: table blocks (runs of consecutive
    '|'-lines, kept whole) and individual non-empty prose lines.

    Returns a list of (start, end, normalized_text) tuples.
    """
    lines, pos = [], 0
    for raw in text.splitlines(keepends=True):
        s = pos
        pos += len(raw)
        lines.append((s, s + len(raw.rstrip("\n")), raw.strip()))

    cands, i, n = [], 0, len(lines)
    while i < n:
        s, e, stripped = lines[i]
        if stripped.startswith("|"):
            j = i
            while j < n and lines[j][2].startswith("|"):
                j += 1
            bs, be = lines[i][0], lines[j - 1][1]
            cands.append((bs, be, norm_map(text[bs:be])[0]))
            i = j
        else:
            if stripped:
                cands.append((s, e, norm_map(stripped)[0]))
            i += 1
    return cands
