from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChunkResult:
    """A single chunk returned from ChromaDB retrieval.

    Field mapping from ChromaDB metadata:
        document_id ← ``company``
        start_char  ← ``char_start``
        end_char    ← ``char_end``
        chunk_index ← parsed from ChromaDB ID (``{company}_{index:04d}``)
    """

    text:        str
    chunk_index: int
    start_char:  int
    end_char:    int
    document_id: str
    score:       float
    metadata:    dict = field(default_factory=dict)


@dataclass
class ReviewResult:
    """Final output of the Retrieval & Review pipeline."""

    final_text:           str
    document_id:          str
    source_chunk_indices: list[int]
    final_start_char:     int
    final_end_char:       int
    review_rounds:        int
    actions_taken:        list[str]
    retrieval_scores:     list[float]
    metadata:             dict
