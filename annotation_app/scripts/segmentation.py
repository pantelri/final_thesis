"""
Text normalization and sentence segmentation for HGB passage texts.

Normalization: literal escape sequences (\\n, \\t) from the CSV source are
converted to real whitespace BEFORE segmentation. The normalized text is what
gets stored in the DB and shown to annotators.

Segmentation strategy:
  - Real newlines are hard sentence boundaries (primary signal: one sentence
    per line in this corpus).
  - Within each line, syntok handles any further splits while correctly
    treating German abbreviations (Vj., Tz., Abs., Nr., ...) as non-terminals.
  - Table blocks (consecutive lines starting with '|') remain one element.
"""
import re

from syntok.segmenter import process as _syntok_process
from syntok._segmentation_states import State as _SegmenterState

# Domain-specific abbreviations absent from syntok's default list.
# syntok 1.4.x keeps its abbreviation set on State.abbreviations (stored
# without the trailing dot) and exposes no public API to extend it, so we
# replace the frozenset with the augmented union at import time.
_DOMAIN_ABBREVS = frozenset({
    "Vj", "Tz", "Abs", "Nr", "TEUR", "Mio", "Mrd", "vgl", "bzw",
    "ggf", "inkl", "exkl", "ca", "Art", "usw", "ggfs", "bzgl",
    "sog", "jew", "entspr", "insb",
})
_SegmenterState.abbreviations = _SegmenterState.abbreviations | _DOMAIN_ABBREVS

_RE_LITERAL_NL = re.compile(r'\\n')
_RE_LITERAL_TAB = re.compile(r'\\t')


def normalize_text(text: str) -> str:
    """Replace literal \\n / \\t escape sequences with real whitespace."""
    text = _RE_LITERAL_NL.sub('\n', text)
    text = _RE_LITERAL_TAB.sub('\t', text)
    return text


def _split_sentences(text: str) -> list[str]:
    """
    Split a text block into sentences.

    Each real newline is treated as a hard sentence boundary first.
    syntok then handles any remaining multi-sentence runs within a line
    while respecting German abbreviations.
    """
    results: list[str] = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # process() yields paragraphs -> sentences -> tokens.
        for paragraph in _syntok_process(line):
            for sentence in paragraph:
                sent = " ".join(t.value for t in sentence).strip()
                if sent:
                    results.append(sent)
    return results


def segment_passage(text: str) -> list[tuple[str, str]]:
    """
    Segment a normalized passage into (element_type, text) tuples.

    Rules
    -----
    - Consecutive '|'-prefixed lines → one 'table' element (unchanged).
    - Markdown heading lines (# …) → stripped text merged into text buffer.
    - All other lines → accumulated in text_buf, flushed as sentences.
      Lines are joined with '\\n' so _split_sentences() can use them as
      hard sentence boundaries.

    Call normalize_text() on the passage before passing it here.
    """
    elements: list[tuple[str, str]] = []
    table_buf: list[str] = []
    text_buf: list[str] = []

    def flush_text() -> None:
        if not text_buf:
            return
        for sent in _split_sentences("\n".join(text_buf)):
            elements.append(("sentence", sent))
        text_buf.clear()

    def flush_table() -> None:
        if not table_buf:
            return
        elements.append(("table", "\n".join(table_buf)))
        table_buf.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            flush_table() if table_buf else flush_text()
            continue
        if stripped.startswith("|"):
            flush_text()
            table_buf.append(line)
        elif stripped.startswith("#"):
            flush_table()
            heading = stripped.lstrip("#").strip()
            if heading:
                text_buf.append(heading)
        else:
            flush_table()
            text_buf.append(stripped)

    flush_text()
    flush_table()
    return elements
