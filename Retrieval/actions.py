from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Literal

import chromadb

from .helpers import _build_chunk_id, _chroma_row_to_chunk, _parse_chunk_id
from .models import ChunkResult

if TYPE_CHECKING:
    from .sentence_splitter import SentenceSplitter

logger = logging.getLogger(__name__)


def apply_trim(
    span_text: str,
    position:  Literal["start", "end"],
    splitter:  "SentenceSplitter",
) -> tuple[str, str]:
    """Remove an incomplete sentence fragment at *position*.

    Returns:
        (new_span_text, removed_fragment). Fragment is empty if none found.
    """
    fragment = splitter.find_fragment(span_text, position)
    if not fragment:
        return span_text, ""

    if position == "start":
        new_text = span_text[len(fragment):].lstrip()
    else:
        new_text = span_text[: len(span_text) - len(fragment)].rstrip()

    logger.debug("Trim '%s': '%s'", position, fragment[:80])
    return new_text, fragment


def apply_remove_sentence(span_text: str, sentence: str) -> str | None:
    """Remove *sentence* from *span_text* by exact string match.

    Returns:
        Modified text, or ``None`` if *sentence* was not found.
    """
    if sentence not in span_text:
        return None
    new_text = span_text.replace(sentence, "", 1)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text).strip()
    return new_text


def fetch_neighbor(
    included:   list[ChunkResult],
    direction:  Literal["previous", "next"],
    collection: chromadb.Collection,
) -> ChunkResult | None:
    """Fetch the adjacent chunk (by index) in the same document.

    Args:
        included:   Currently included chunks.
        direction:  ``"previous"`` → prepend; ``"next"`` → append.
        collection: ChromaDB collection to query.

    Returns:
        A new ``ChunkResult``, or ``None`` if the neighbor does not exist.
    """
    if not included:
        return None

    if direction == "previous":
        boundary = min(included, key=lambda c: c.start_char)
    else:
        boundary = max(included, key=lambda c: c.end_char)

    chunk_id = boundary.metadata.get("_chunk_id", "")
    if not chunk_id:
        logger.warning("expand_neighbor: _chunk_id nicht in Metadaten gefunden.")
        return None

    company, idx = _parse_chunk_id(chunk_id)
    neighbor_idx = idx - 1 if direction == "previous" else idx + 1
    if neighbor_idx < 1:
        logger.debug("expand_neighbor: Index %d < 1 – kein Vorgänger.", neighbor_idx)
        return None

    neighbor_id = _build_chunk_id(company, neighbor_idx)

    try:
        res = collection.get(ids=[neighbor_id], include=["documents", "metadatas"])
    except Exception as exc:
        logger.warning("expand_neighbor: ChromaDB-Fehler bei '%s': %s", neighbor_id, exc)
        return None

    if not res["ids"]:
        logger.debug("expand_neighbor: Chunk '%s' nicht in Collection.", neighbor_id)
        return None

    return _chroma_row_to_chunk(
        chroma_id = res["ids"][0],
        document  = res["documents"][0],
        metadata  = res["metadatas"][0],
        score     = 0.0,
    )
