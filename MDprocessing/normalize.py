"""Whitespace/punctuation-insensitive normalization for .md text matching."""

# Markdown markers re-included at a span's left edge (headings, list bullets,
# table pipes) when expanding a normalized match back to verbatim text.
HEADING_LEFT = set("#*->| \t")


def norm_map(text: str):
    """Return (alphanumeric-lowercased string, list mapping each normalized char
    back to its character offset in `text`).

    Reducing to alphanumerics makes matching robust against tokenizer spacing
    ("65,9 %" vs "65,9%"), hyphenation ("Amazon-Gruppe" vs "Amazon Gruppe") and
    other punctuation/whitespace differences.
    """
    out, idx = [], []
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
    return "".join(out), idx


def find_all(haystack: str, needle: str):
    """All start offsets of `needle` in `haystack` (overlapping allowed)."""
    pos, start = [], 0
    while needle:
        p = haystack.find(needle, start)
        if p < 0:
            break
        pos.append(p)
        start = p + 1
    return pos


def expand_span(text: str, start: int, end: int):
    """Grow a normalized-match span to include leading markdown markers and
    trailing punctuation, without crossing a line boundary."""
    while start > 0 and text[start - 1] in HEADING_LEFT and text[start - 1] != "\n":
        start -= 1
    while end < len(text) and text[end] != "\n" and not text[end].isalnum():
        end += 1
    return start, end
