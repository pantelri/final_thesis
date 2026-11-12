from __future__ import annotations

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

_ABBREV_PATTERN = re.compile(
    r'\b('
    r'Abs|Nr|Art|Tz|§\s*\d+'
    r'|i\.V\.m|i\.d\.F|i\.S\.d|i\.S\.v|i\.H\.v|i\.R\.d'
    r'|gem|vgl|etc|bzw|z\.B|u\.a|o\.g|o\.ä|sog|ggf|evtl|ca|inkl|exkl|zzgl|abzgl'
    r'|Dr|Prof|Dipl|Hr|Fr|Hrsg|Aufl|Bd|Jg|Jh|Sp|Abs'
    r'|Mio|Mrd|GmbH|AG|KG|OHG|UG|mbH|Co'
    r'|vs|max|min|std|ggü|bspw|insb|usw'
    r')\.',
    re.IGNORECASE,
)

_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ"\(])')

_PLACEHOLDER = "\x00"


def _protect_abbrevs(text: str) -> str:
    return _ABBREV_PATTERN.sub(lambda m: m.group().replace(".", _PLACEHOLDER), text)


def _restore_abbrevs(text: str) -> str:
    return text.replace(_PLACEHOLDER, ".")


class SentenceSplitter:
    """Split German legal/financial text into sentences.

    Tries ``spacy`` (``de_core_news_sm``) first; falls back to a regex that
    guards against common German abbreviations.
    """

    def __init__(self, use_spacy: bool = True) -> None:
        self._nlp = None
        if use_spacy:
            try:
                import spacy  # type: ignore[import]
                self._nlp = spacy.load("de_core_news_sm")
                logger.debug("SentenceSplitter: spacy de_core_news_sm geladen.")
            except Exception:
                logger.debug("SentenceSplitter: spacy nicht verfügbar – Regex-Fallback aktiv.")

    def split(self, text: str) -> list[str]:
        if self._nlp is not None:
            doc = self._nlp(text)
            return [s.text.strip() for s in doc.sents if s.text.strip()]
        return self._split_regex(text)

    def find_fragment(self, text: str, position: Literal["start", "end"]) -> str:
        """Return an incomplete sentence fragment at *position*, or empty string."""
        sentences = self.split(text)
        if not sentences:
            return ""

        if position == "start":
            first = sentences[0]
            if not re.match(r'^[A-ZÄÖÜ0-9"\(§]', first):
                return first
            return ""

        last = sentences[-1]
        if not re.search(r'[.!?]["»]?\s*$', last):
            return last
        return ""

    @staticmethod
    def _split_regex(text: str) -> list[str]:
        protected = _protect_abbrevs(text)
        parts     = _SENTENCE_BOUNDARY.split(protected)
        return [_restore_abbrevs(p).strip() for p in parts if p.strip()]
