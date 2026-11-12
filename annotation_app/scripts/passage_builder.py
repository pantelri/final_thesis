"""Assemble an annotation passage verbatim from a .md document, given the
annotator feedback (sentences to drop, passages to add).

The .md-locating logic lives in the project-wide `MDprocessing` package; this
module only orchestrates it for the annotation use case.
"""
from MDprocessing import MdDocument

# Separator between non-contiguous passages. On its own line (blank lines around)
# so re-segmentation keeps table blocks clean instead of merging a table with the
# prose that follows it.
SEP = "\n\n[...]\n\n"
FUZZY_REVIEW = 0.75  # below this .md similarity, flag a piece for manual review


def _content(s: str) -> bool:
    return any(ch.isalnum() for ch in s)


def _assemble(doc: MdDocument, spans: list[tuple[int, int]]) -> str:
    """Order spans by document position; join contiguous runs verbatim and
    separate non-contiguous parts (skipped/removed content) with SEP."""
    spans.sort()
    blocks, cur = [], None
    for s, e in spans:
        if cur is None:
            cur = [s, e]
        elif _content(doc.slice(cur[1], s)):     # real content skipped -> new block
            blocks.append(doc.slice(*cur).strip())
            cur = [s, e]
        else:                                    # contiguous/overlapping -> extend
            cur[1] = max(cur[1], e)
    if cur:
        blocks.append(doc.slice(*cur).strip())
    return SEP.join(b for b in blocks if b)


def build_passage(doc, sentences, irrelevant, suggested):
    """Return (new_passage_text, flags).

    sentences : list[(idx, element_type, text)] in document order
    irrelevant: set[int] of sentence idx to drop
    suggested : list[(passage_text, source_ref)] to add (LLM output)
    """
    flags, spans, cursor = [], [], 0

    # Retained content -> verbatim .md. Stored elements may bundle several source
    # spans behind embedded "[...]" markers (a segmentation artifact); split first.
    for idx, _etype, txt in sentences:
        if idx in irrelevant:
            continue
        for part in txt.split("[...]"):
            if not _content(part):
                continue
            span = doc.locate_monotonic(part, cursor)
            if span:
                spans.append(span)
                cursor = span[1]
                continue
            span, ratio = doc.locate_fuzzy(part, prefer=cursor)
            if span:
                spans.append(span)
                cursor = span[1]
                tag = "REVIEW low similarity" if ratio < FUZZY_REVIEW else "used closest .md"
                flags.append(f"sentence idx{idx}: not verbatim -> {tag} ({ratio:.2f})")
            else:
                flags.append(f"sentence idx{idx}: NO .md match -> dropped, REVIEW")

    anchor = spans[len(spans) // 2][0] if spans else 0

    # Suggested passages (LLM) -> verbatim .md, positioned via source_ref/anchor.
    for sptxt, sref in suggested:
        ref_hits = doc.locate_exact(sref) if sref else []
        prefer = ref_hits[0][1] if ref_hits else anchor
        exact = doc.locate_exact(sptxt)
        if exact:
            spans.append(min(exact, key=lambda c: abs(c[0] - prefer)))
            if len(exact) > 1:
                flags.append(f"suggested {(sref or '')[:40]!r}: {len(exact)} verbatim "
                             f"matches -> chose nearest source_ref")
            continue
        span, ratio = doc.locate_fuzzy(sptxt, prefer=prefer)
        if span:
            spans.append(span)
            flags.append(f"suggested {(sref or '')[:40]!r}: not verbatim (LLM) "
                         f"-> closest .md passage ({ratio:.2f})")
        else:
            flags.append(f"suggested {(sref or '')[:50]!r}: NO .md match -> skipped, REVIEW")

    return _assemble(doc, spans), flags
