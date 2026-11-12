"""Split a Markdown document by headings, tracking absolute char offsets.

Each returned section dict:
    heading_path : str   "H1 > H2 > H3" breadcrumb
    heading      : str   innermost heading text
    level        : int   1–6
    char_start   : int   absolute offset in md_text (first char of content)
    char_end     : int   absolute offset in md_text (exclusive)
    text         : str   md_text[char_start:char_end]
"""
from __future__ import annotations
import re

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$', re.MULTILINE)


def split_by_headings(md_text: str) -> list[dict]:
    """
    Split md_text into sections at every Markdown heading (H1–H6).
    Consecutive headings without content in between produce no section.
    Preamble content before the first heading is returned as level-0 section.
    """
    matches = list(_HEADING_RE.finditer(md_text))
    sections: list[dict] = []

    if not matches:
        if md_text.strip():
            sections.append(_section('', '', 0, 0, len(md_text), md_text))
        return sections

    stack: dict[int, str] = {}

    # Preamble before first heading
    pre_end = matches[0].start()
    if md_text[:pre_end].strip():
        sections.append(_section('', '', 0, 0, pre_end, md_text[:pre_end]))

    for idx, m in enumerate(matches):
        level   = len(m.group(1))
        heading = m.group(2).strip()

        # Update heading stack: remove deeper levels
        stack[level] = heading
        for deeper in [l for l in list(stack.keys()) if l > level]:
            del stack[deeper]

        path = ' > '.join(stack[l] for l in sorted(stack.keys()))

        # Content starts on the line after the heading
        cs = m.end()
        if cs < len(md_text) and md_text[cs] == '\n':
            cs += 1

        # Content ends at the start of the next heading (or end of file)
        ce = matches[idx + 1].start() if idx + 1 < len(matches) else len(md_text)

        text = md_text[cs:ce]
        if text.strip():
            sections.append(_section(path, heading, level, cs, ce, text))

    return sections


def _section(path: str, heading: str, level: int,
             cs: int, ce: int, text: str) -> dict:
    return {
        'heading_path': path,
        'heading':      heading,
        'level':        level,
        'char_start':   cs,
        'char_end':     ce,
        'text':         text,
    }
