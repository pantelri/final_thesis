"""MdDocument: locate verbatim text spans within a Markdown document."""
from difflib import SequenceMatcher
from pathlib import Path

from .candidates import md_candidates
from .normalize import expand_span, find_all, norm_map

Span = tuple[int, int]


class MdDocument:
    """Wraps a .md text and finds where a query string sits inside it.

    Matching is alphanumeric-normalized, so tokenizer spacing, hyphenation and
    punctuation differences do not prevent a hit. `locate_fuzzy` falls back to
    the most similar verbatim unit when no exact match exists (e.g. for an
    LLM-reworded passage, or content that drifted from the current .md).
    """

    def __init__(self, text: str):
        self.text = text
        self._norm, self._map = norm_map(text)
        self._cands = md_candidates(text)

    @classmethod
    def from_file(cls, path) -> "MdDocument":
        return cls(Path(path).read_text(encoding="utf-8"))

    def slice(self, start: int, end: int) -> str:
        return self.text[start:end]

    def _spans(self, query: str) -> list[Span]:
        qn, _ = norm_map(query)
        if not qn:
            return []
        return [expand_span(self.text, self._map[p], self._map[p + len(qn) - 1] + 1)
                for p in find_all(self._norm, qn)]

    def locate_exact(self, query: str) -> list[Span]:
        """Every verbatim span whose normalized text equals the query."""
        return self._spans(query)

    def locate_monotonic(self, query: str, lo: int = 0) -> Span | None:
        """Earliest exact span starting at/after `lo`; else the global earliest."""
        spans = self._spans(query)
        if not spans:
            return None
        forward = [s for s in spans if s[0] >= lo]
        return forward[0] if forward else spans[0]

    def locate_fuzzy(self, query: str, prefer: int | None = None, topk: int = 4):
        """Most-similar verbatim unit for a query not present verbatim. Among the
        top-k by similarity, prefer the candidate nearest to offset `prefer` (a
        source_ref locator or content anchor). Returns ((start, end), ratio)."""
        qn = norm_map(query)[0]
        if not qn:
            return None, 0.0
        scored = [(SequenceMatcher(None, qn, cn, autojunk=False).ratio(), bs, be)
                  for bs, be, cn in self._cands if cn]
        if not scored:
            return None, 0.0
        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:topk]
        r, bs, be = (min(top, key=lambda t: abs(t[1] - prefer))
                     if prefer is not None else top[0])
        return expand_span(self.text, bs, be), r
